import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload as UploadIcon, FileText, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { uploadDocumentAPI } from "@/lib/apiService";

const Upload = () => {
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const navigate = useNavigate();

  const uploadMutation = useMutation<any, Error, File>({
    mutationFn: async (file) => {
      const formData = new FormData();
      formData.append("file", file);
      const response = await uploadDocumentAPI(formData);
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(`Document "${data.filename || uploadedFile?.name}" uploaded successfully! Processing started.`);
      setUploadedFile(null);
      if (data.filename) {
        navigate(`/analyze/${data.filename}`);
      }
    },
    onError: (error) => {
      toast.error(`Upload failed: ${error.message}`);
    },
  });

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      handleFile(files[0]);
    }
  };

  const handleFile = (file: File) => {
    if (file.type !== "application/pdf") {
      toast.error("Please upload a PDF file");
      return;
    }
    
    setUploadedFile(file);
    toast.success("File ready for upload");
  };

  const handleUpload = async () => {
    if (!uploadedFile) return;
    
    uploadMutation.mutate(uploadedFile);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload SOTR Document</h1>
          <p className="text-gray-600">Upload your Statement of Technical Requirements (SOTR) document for AI analysis</p>
        </div>

        <div className="max-w-2xl mx-auto">
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Document Upload</CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive 
                    ? "border-blue-500 bg-blue-50" 
                    : "border-gray-300 hover:border-gray-400"
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                {uploadedFile ? (
                  <div className="space-y-4">
                    <CheckCircle className="w-16 h-16 text-green-500 mx-auto" />
                    <div>
                      <p className="text-lg font-medium text-gray-900">{uploadedFile.name}</p>
                      <p className="text-gray-500">{(uploadedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                    <Button 
                      onClick={handleUpload} 
                      disabled={uploadMutation.isPending}
                      className="w-full"
                    >
                      {uploadMutation.isPending ? (
                        <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Uploading...</>
                      ) : (
                        "Upload Document"
                      )}
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <UploadIcon className="w-16 h-16 text-gray-400 mx-auto" />
                    <div>
                      <p className="text-lg font-medium text-gray-900">Drop your PDF here</p>
                      <p className="text-gray-500">or click to browse files</p>
                    </div>
                    <input
                      type="file"
                      accept=".pdf"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleFile(file);
                      }}
                      className="hidden"
                      id="file-upload"
                    />
                    <label htmlFor="file-upload">
                      <Button variant="outline" className="cursor-pointer" asChild>
                        <span>Browse Files</span>
                      </Button>
                    </label>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Upload Guidelines */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-blue-600" />
                Upload Guidelines
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-gray-600">
                <li className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Only PDF files are supported
                </li>
                <li className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Maximum file size: 50MB
                </li>
                <li className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Ensure the document contains clear technical requirements
                </li>
                <li className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Text-based PDFs work best for analysis
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Upload;
