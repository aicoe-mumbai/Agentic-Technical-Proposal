import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, FileText, Layout, Zap, ArrowRight, RefreshCw, ServerCrash, Inbox, Files } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listDocumentsAPI, listTemplatesAPI } from "@/lib/apiService";
import { format } from 'date-fns';

// Define DocumentSummaryItem interface matching backend model
interface DocumentSummaryItem {
  doc_id: string;
  filename: string;
  status: string;
  created_at?: string;
  total_pages?: number;
}

// Define interface for templates displayed on the dashboard
interface DashboardTemplateItem {
  name: string;
  tocLineCount: number;
  // project_TOC: string; // Keep if full TOC is needed later
}

// Define the structure of the raw template data from the API
interface BackendTemplateDetail {
  project_TOC: string;
  file_path: string;
}

interface BackendTemplatesResponse {
  templates: Record<string, BackendTemplateDetail>;
}

const Dashboard = () => {
  const navigate = useNavigate();
  // Fetch recent documents
  const {
    data: documentsData,
    isLoading: isLoadingDocuments,
    error: documentsError,
    refetch: refetchDocuments
  } = useQuery<{
    documents: DocumentSummaryItem[];
  }, Error>({
    queryKey: ["allDocuments"],
    queryFn: async () => {
      const response = await listDocumentsAPI();
      if (response.data && Array.isArray(response.data.documents)) {
          return response.data;
      } else {
          console.warn("Unexpected data structure from listDocumentsAPI", response.data);
          return { documents: [] };
      }
    },
    staleTime: 5 * 60 * 1000,
    refetchInterval: 30000,
  });

  const recentDocuments = documentsData?.documents || [];

  // Fetch available templates
  const {
    data: templatesApiResponse, // Store the raw API response
    isLoading: isLoadingTemplates,
    error: templatesError,
    refetch: refetchTemplates
  } = useQuery<BackendTemplatesResponse, Error>({ // Use BackendTemplatesResponse for raw data
    queryKey: ["allTemplatesDashboard"],
    queryFn: async () => {
      const response = await listTemplatesAPI();
      // Assuming response.data is BackendTemplatesResponse { templates: { ... } }
      return response.data; 
    },
    staleTime: 10 * 60 * 1000, // Cache for 10 minutes
  });

  // Transform templates data for display
  const availableTemplates: DashboardTemplateItem[] = templatesApiResponse?.templates
    ? Object.entries(templatesApiResponse.templates).map(([name, details]) => ({
        name,
        tocLineCount: details.project_TOC?.split('\\n').length || 0,
        // project_TOC: details.project_TOC,
      }))
    : [];

  const getStatusColor = (status: string) => {
    if (status === 'processed') return 'bg-green-100 text-green-800';
    if (status === 'error') return 'bg-red-100 text-red-800';
    if (status === 'uploading' || status === 'processing') return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Technical Proposal Generator</h1>
          <p className="text-lg text-gray-600">Transform SOTR documents into compelling technical proposals with AI</p>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Link to="/upload">
            <Card className="hover:shadow-lg transition-shadow cursor-pointer border-2 hover:border-blue-300">
              <CardContent className="p-6 text-center">
                <Upload className="w-12 h-12 text-blue-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">Upload Document</h3>
                <p className="text-gray-600">Upload a new SOTR document for analysis</p>
              </CardContent>
            </Card>
          </Link>

          <Link to="/templates">
            <Card className="hover:shadow-lg transition-shadow cursor-pointer border-2 hover:border-green-300">
              <CardContent className="p-6 text-center">
                <Layout className="w-12 h-12 text-green-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">Manage Templates</h3>
                <p className="text-gray-600">Create and organize proposal templates</p>
              </CardContent>
            </Card>
          </Link>

          <Link to="/analyze">
            <Card className="hover:shadow-lg transition-shadow cursor-pointer border-2 hover:border-purple-300">
              <CardContent className="p-6 text-center">
                <Zap className="w-12 h-12 text-purple-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">Analyze Document</h3>
                <p className="text-gray-600">Create AI-powered technical proposals (select document on next page)</p>
              </CardContent>
            </Card>
          </Link>
        </div>

        {/* Recent Documents and Templates */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Documents Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Recent Documents
                </div>
                <Button variant="ghost" size="sm" onClick={() => refetchDocuments()} disabled={isLoadingDocuments}>
                  <RefreshCw className={`w-4 h-4 ${isLoadingDocuments ? 'animate-spin' : ''}`} />
                </Button>
              </CardTitle>
              <CardDescription>Your recently uploaded SOTR documents and their status.</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingDocuments && (
                <div className="text-center py-4">
                  <RefreshCw className="w-6 h-6 mx-auto animate-spin text-gray-500" />
                  <p className="text-sm text-gray-500 mt-2">Loading documents...</p>
                </div>
              )}
              {documentsError && (
                <div className="text-center py-4 text-red-600">
                  <ServerCrash className="w-6 h-6 mx-auto mb-2" />
                  <p className="font-semibold">Failed to load documents</p>
                  <p className="text-sm">{documentsError.message}</p>
                  <Button variant="outline" size="sm" onClick={() => refetchDocuments()} className="mt-2">Retry</Button>
                </div>
              )}
              {!isLoadingDocuments && !documentsError && recentDocuments.length === 0 && (
                <div className="text-center py-4 text-gray-500">
                  <Inbox className="w-12 h-12 mx-auto mb-3" />
                  <h4 className="font-semibold mb-1">No Documents Yet</h4>
                  <p className="text-sm">Upload your first SOTR document to get started!</p>
                  <Button asChild className="mt-3">
                    <Link to="/upload"><Upload className="w-4 h-4 mr-2"/> Upload Now</Link>
                  </Button>
                </div>
              )}
              {!isLoadingDocuments && !documentsError && recentDocuments.length > 0 && (
                <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                  {recentDocuments.map((doc) => (
                    <div 
                      key={doc.doc_id} 
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
                      onClick={() => navigate(`/analyze/${doc.doc_id}`)}
                    >
                      <div>
                        <p className="font-medium text-gray-900 truncate max-w-xs" title={doc.filename}>{doc.filename}</p>
                        <p className="text-xs text-gray-500">
                          {doc.created_at ? `Uploaded ${format(new Date(doc.created_at), 'MMM d, yyyy HH:mm')}` : 'Date N/A'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(doc.status)}`}>
                          {doc.status}
                        </span>
                        <ArrowRight className="w-4 h-4 text-gray-400" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Available Templates Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Files className="w-5 h-5" />
                  Available Templates
                </div>
                <Button variant="ghost" size="sm" onClick={() => refetchTemplates()} disabled={isLoadingTemplates}>
                  <RefreshCw className={`w-4 h-4 ${isLoadingTemplates ? 'animate-spin' : ''}`} />
                </Button>
              </CardTitle>
              <CardDescription>Your created proposal templates.</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingTemplates && (
                <div className="text-center py-4">
                  <RefreshCw className="w-6 h-6 mx-auto animate-spin text-gray-500" />
                  <p className="text-sm text-gray-500 mt-2">Loading templates...</p>
                </div>
              )}
              {templatesError && (
                <div className="text-center py-4 text-red-600">
                  <ServerCrash className="w-6 h-6 mx-auto mb-2" />
                  <p className="font-semibold">Failed to load templates</p>
                  <p className="text-sm">{templatesError.message}</p>
                  <Button variant="outline" size="sm" onClick={() => refetchTemplates()} className="mt-2">Retry</Button>
                </div>
              )}
              {!isLoadingTemplates && !templatesError && availableTemplates.length === 0 && (
                 <div className="text-center py-4 text-gray-500">
                  <Inbox className="w-12 h-12 mx-auto mb-3" />
                  <h4 className="font-semibold mb-1">No Templates Yet</h4>
                  <p className="text-sm">Create your first proposal template to see it here.</p>
                  <Button asChild className="mt-3">
                    <Link to="/templates"><Layout className="w-4 h-4 mr-2"/> Create Template</Link>
                  </Button>
                </div>
              )}
              {!isLoadingTemplates && !templatesError && availableTemplates.length > 0 && (
                <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                  {availableTemplates.map((template) => (
                    <div 
                      key={template.name} 
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
                      onClick={() => navigate('/templates')}
                    >
                      <div>
                        <p className="font-medium text-gray-900 truncate max-w-xs" title={template.name}>{template.name}</p>
                        <p className="text-sm text-gray-500">
                          {template.tocLineCount > 0 ? `${template.tocLineCount} section(s) in TOC` : 'No TOC details'}
                        </p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-gray-400" />
                    </div>
                  ))}
                </div>
              )}
              <Link to="/templates">
                <Button variant="outline" className="w-full mt-4">
                  Manage All Templates
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
