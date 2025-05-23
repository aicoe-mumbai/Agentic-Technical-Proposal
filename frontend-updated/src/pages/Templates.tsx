import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Layout, Plus, Edit, Trash2, FileText, Loader2, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter, DialogClose
} from "@/components/ui/dialog";

import { listTemplatesAPI, createTemplateAPI, deleteTemplateAPI, getTemplateDataAPI, updateTemplateAPI } from "@/lib/apiService";

// Interface matching backend response for a single template
interface Template {
  project_name: string;
  project_TOC: string;
  file_path?: string;
}

// Interface for template data from Excel
interface TemplateData {
  [key: string]: string;
}

const Templates = () => {
  const queryClient = useQueryClient();

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newTemplateName, setNewTemplateName] = useState("");
  const [newTemplateTOC, setNewTemplateTOC] = useState("");
  const [newTemplateFile, setNewTemplateFile] = useState<File | null>(null);

  // State for Edit Template Dialog
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [editTemplateTOC, setEditTemplateTOC] = useState("");
  const [editTemplateFile, setEditTemplateFile] = useState<File | null>(null);

  const [viewDataDialogOpen, setViewDataDialogOpen] = useState(false);
  const [selectedTemplateForData, setSelectedTemplateForData] = useState<Template | null>(null);

  // Fetching templates
  const { data: templates = [], isLoading: isLoadingTemplates, error: templatesError } = useQuery<Template[], Error>({
    queryKey: ["templates"],
    queryFn: async () => {
      const response = await listTemplatesAPI();
      const templatesData = response.data.templates; // This is an object
      if (typeof templatesData === 'object' && templatesData !== null && !Array.isArray(templatesData)) {
        // Transform the object into an array
        return Object.entries(templatesData).map(([projectName, details]) => ({
          project_name: projectName,
          project_TOC: (details as any).project_TOC,
          file_path: (details as any).file_path,
        }));
      } else if (Array.isArray(templatesData)) {
        return templatesData; // If it's already an array, return as is
      }
      return []; // Return empty array if not an object or null, or if transformation fails
    },
  });

  // Fetching template data (Excel) - triggered manually
  const { data: templateExcelData, isLoading: isLoadingTemplateData, mutate: fetchTemplateData, error: templateDataError } = useMutation<TemplateData, Error, string>({
    mutationFn: async (projectName) => {
      const response = await getTemplateDataAPI(projectName);
      return response.data;
    },
    onSuccess: () => {
      setViewDataDialogOpen(true);
    },
    onError: (error) => {
      toast.error(`Failed to fetch template data: ${error.message}`);
      setSelectedTemplateForData(null); // Clear selection on error
    }
  });


  // Creating a new template
  const createTemplateMutation = useMutation<Template, Error, FormData>({
    mutationFn: createTemplateAPI,
    onSuccess: () => {
      toast.success("Template created successfully!");
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      setShowCreateDialog(false);
      setNewTemplateName("");
      setNewTemplateTOC("");
      setNewTemplateFile(null);
    },
    onError: (error) => {
      toast.error(`Failed to create template: ${error.message}`);
    },
  });

  // Deleting a template
  const deleteTemplateMutation = useMutation<void, Error, string>({
    mutationFn: deleteTemplateAPI,
    onSuccess: () => {
      toast.success("Template deleted successfully!");
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
    onError: (error) => {
      // Log the actual error object for more details
      console.error("Delete template error:", error);
      toast.error(`Failed to delete template: ${error.message}`);
    },
  });

  // Updating an existing template
  const updateTemplateMutation = useMutation<Template, Error, { projectName: string; formData: FormData }>({
    mutationFn: ({ projectName, formData }) => updateTemplateAPI(projectName, formData),
    onSuccess: (data) => {
      toast.success(`Template "${data.project_name}" updated successfully!`);
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      setShowEditDialog(false);
      setEditingTemplate(null);
      setEditTemplateTOC("");
      setEditTemplateFile(null);
    },
    onError: (error) => {
      toast.error(`Failed to update template: ${error.message}`);
    },
  });

  const handleCreateTemplateSubmit = () => {
    if (!newTemplateName.trim()) {
      toast.error("Please enter a template name");
      return;
    }
    if (!newTemplateTOC.trim()) {
      toast.error("Please enter a Table of Contents");
      return;
    }

    const formData = new FormData();
    formData.append("project_name", newTemplateName);
    formData.append("project_TOC", newTemplateTOC);
    if (newTemplateFile) {
      formData.append("excel_file", newTemplateFile);
    }
    createTemplateMutation.mutate(formData);
  };

  const handleOpenEditDialog = (template: Template) => {
    setEditingTemplate(template);
    setEditTemplateTOC(template.project_TOC);
    setEditTemplateFile(null); // Reset file input for edit
    setShowEditDialog(true);
  };

  const handleEditTemplateSubmit = () => {
    if (!editingTemplate) return;
    if (!editTemplateTOC.trim()) {
      toast.error("Table of Contents cannot be empty.");
      return;
    }

    const formData = new FormData();
    formData.append("project_TOC", editTemplateTOC); // Changed from template_update_request to match form field
    if (editTemplateFile) {
      formData.append("excel_file", editTemplateFile);
    }
    
    updateTemplateMutation.mutate({ projectName: editingTemplate.project_name, formData });
  };

  const handleViewData = (template: Template) => {
    setSelectedTemplateForData(template);
    fetchTemplateData(template.project_name);
  };

  console.log("isLoadingTemplates:", isLoadingTemplates);
  console.log("templates data:", templates);
  console.log("templatesError:", templatesError);

  if (templatesError) {
    return (
      <div className="flex items-center justify-center h-full text-red-600">
        <AlertCircle className="w-6 h-6 mr-2" /> Error fetching templates: {templatesError.message}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Proposal Templates</h1>
            <p className="text-gray-600">Manage your reusable proposal templates.</p>
          </div>
          <Button onClick={() => setShowCreateDialog(true)} className="flex items-center gap-2">
            <Plus className="w-5 h-5" />
            New Template
          </Button>
        </div>

        {/* Create Template Dialog */}
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent className="sm:max-w-[525px]">
            <DialogHeader>
              <DialogTitle>Create New Template</DialogTitle>
              <DialogDescription>
                Fill in the details for your new proposal template.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div>
                <label htmlFor="templateName" className="block text-sm font-medium mb-1">Template Name</label>
                <Input
                  id="templateName"
                  value={newTemplateName}
                  onChange={(e) => setNewTemplateName(e.target.value)}
                  placeholder="E.g., Software Development Proposal"
                />
              </div>
              <div>
                <label htmlFor="templateTOC" className="block text-sm font-medium mb-1">Table of Contents</label>
                <Textarea
                  id="templateTOC"
                  value={newTemplateTOC}
                  onChange={(e) => setNewTemplateTOC(e.target.value)}
                  placeholder="Enter section names, one per line..."
                  className="h-32"
                />
              </div>
              <div>
                <label htmlFor="templateFile" className="block text-sm font-medium mb-1">Excel File (Optional)</label>
                <Input
                  id="templateFile"
                  type="file"
                  accept=".xlsx, .xls"
                  onChange={(e) => setNewTemplateFile(e.target.files ? e.target.files[0] : null)}
                  className="file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
                 {newTemplateFile && <p className="text-sm text-gray-500 mt-1">{newTemplateFile.name}</p>}
              </div>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button onClick={handleCreateTemplateSubmit} disabled={createTemplateMutation.isPending}>
                {createTemplateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Template
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        
        {/* Edit Template Dialog */}
        {editingTemplate && (
          <Dialog open={showEditDialog} onOpenChange={(isOpen) => {
            if (!isOpen) {
              setEditingTemplate(null); // Clear selection when closing
              setEditTemplateTOC("");
              setEditTemplateFile(null);
            }
            setShowEditDialog(isOpen);
          }}>
            <DialogContent className="sm:max-w-[525px]">
              <DialogHeader>
                <DialogTitle>Edit Template: {editingTemplate.project_name}</DialogTitle>
                <DialogDescription>
                  Update the Table of Contents and optionally replace the Excel file.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div>
                  <label htmlFor="editTemplateName" className="block text-sm font-medium mb-1">Template Name (Read-only)</label>
                  <Input
                    id="editTemplateName"
                    value={editingTemplate.project_name}
                    readOnly
                    className="bg-gray-100"
                  />
                </div>
                <div>
                  <label htmlFor="editTemplateTOC" className="block text-sm font-medium mb-1">Table of Contents</label>
                  <Textarea
                    id="editTemplateTOC"
                    value={editTemplateTOC}
                    onChange={(e) => setEditTemplateTOC(e.target.value)}
                    placeholder="Enter section names, one per line..."
                    className="h-32"
                  />
                </div>
                <div>
                  <label htmlFor="editTemplateFile" className="block text-sm font-medium mb-1">Replace Excel File (Optional)</label>
                  <Input
                    id="editTemplateFile"
                    type="file"
                    accept=".xlsx, .xls"
                    onChange={(e) => setEditTemplateFile(e.target.files ? e.target.files[0] : null)}
                    className="file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  />
                  {editTemplateFile && <p className="text-sm text-gray-500 mt-1">New file: {editTemplateFile.name}</p>}
                  {!editTemplateFile && editingTemplate.file_path && <p className="text-sm text-gray-500 mt-1">Current file: {editingTemplate.file_path.split("/").pop()}</p>}
                  {!editTemplateFile && !editingTemplate.file_path && <p className="text-sm text-gray-500 mt-1">No Excel file currently associated.</p>}
                </div>
              </div>
              <DialogFooter>
                <DialogClose asChild>
                  <Button variant="outline">Cancel</Button>
                </DialogClose>
                <Button onClick={handleEditTemplateSubmit} disabled={updateTemplateMutation.isPending}>
                  {updateTemplateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Save Changes
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
        
        {/* View Template Data Dialog */}
        {selectedTemplateForData && (
          <Dialog open={viewDataDialogOpen} onOpenChange={(isOpen) => {
            if (!isOpen) {
                setSelectedTemplateForData(null); // Clear selection when closing
            }
            setViewDataDialogOpen(isOpen);
          }}>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Data for: {selectedTemplateForData.project_name}</DialogTitle>
                 <DialogDescription>
                  {templateDataError ? `Error: ${templateDataError.message}` : "Data from the template's Excel file."}
                </DialogDescription>
              </DialogHeader>
              <div className="mt-4 max-h-96 overflow-y-auto">
                {isLoadingTemplateData && <div className="flex justify-center items-center p-4"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>}
                {!isLoadingTemplateData && templateExcelData && Object.keys(templateExcelData).length > 0 ? (
                  <ul className="space-y-1">
                    {Object.entries(templateExcelData).map(([key, value]) => (
                      <li key={key} className="text-sm p-2 border-b last:border-b-0">
                        <span className="font-semibold">{key}:</span> {String(value)}
                      </li>
                    ))}
                  </ul>
                ) : (
                  !isLoadingTemplateData && !templateDataError && <p className="text-sm text-gray-500">No data found or file not present.</p>
                )}
              </div>
              <DialogFooter className="sm:justify-start">
                <DialogClose asChild>
                  <Button type="button" variant="secondary">Close</Button>
                </DialogClose>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}


        {/* Templates Grid */}
        {isLoadingTemplates && (
          <div className="flex justify-center items-center py-10">
            <Loader2 className="w-12 h-12 animate-spin text-blue-600" />
          </div>
        )}
        {!isLoadingTemplates && templates.length === 0 && (
          <p className="text-center text-gray-500 py-10">No templates found. Create one to get started!</p>
        )}
        {!isLoadingTemplates && templates.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((template) => (
              <Card key={template.project_name} className="hover:shadow-xl transition-shadow duration-300 ease-in-out flex flex-col">
                <CardHeader className="pb-4">
                <div className="flex items-start justify-between">
                    <Layout className="w-10 h-10 text-blue-600 mb-2" />
                  <div className="flex gap-1">
                      {/* Edit button can be implemented later */}
                      {/* <Button variant="ghost" size="icon" className="h-8 w-8"> <Edit className="w-4 h-4" /> </Button> */}
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-600 hover:text-gray-800" onClick={() => handleOpenEditDialog(template)}>
                      <Edit className="w-4 h-4" />
                    </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500 hover:text-red-700" disabled={deleteTemplateMutation.isPending}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                            <AlertDialogDescription>
                              This action cannot be undone. This will permanently delete the template "{template.project_name}".
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => {
                                console.log("Attempting to delete template with project_name:", template.project_name);
                                deleteTemplateMutation.mutate(template.project_name);
                              }}
                              disabled={deleteTemplateMutation.isPending}
                              className="bg-red-600 hover:bg-red-700"
                            >
                              {deleteTemplateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>
                  <CardTitle className="text-xl font-semibold text-gray-800">{template.project_name}</CardTitle>
              </CardHeader>
                <CardContent className="flex-grow flex flex-col justify-between">
                  <div>
                    <p className="text-gray-600 text-sm mb-3 line-clamp-3">
                        <span className="font-medium">TOC: </span>{template.project_TOC || "No Table of Contents provided."}
                    </p>
                    {template.file_path && (
                      <Button variant="outline" size="sm" className="mb-4 w-full text-blue-600 border-blue-500 hover:bg-blue-50" onClick={() => handleViewData(template)}>
                        <FileText className="w-4 h-4 mr-2" /> View Excel Data
                      </Button>
                    )}
                    {!template.file_path && (
                        <p className="text-xs text-gray-400 mb-4 italic">No Excel data associated.</p>
                    )}
                  </div>
                  <Button className="w-full mt-auto bg-blue-600 hover:bg-blue-700" onClick={() => handleOpenEditDialog(template)}>
                     <Edit className="w-4 h-4 mr-2" /> Edit Template
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
        )}
      </div>
    </div>
  );
};

export default Templates;
