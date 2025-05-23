import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogClose } from "@/components/ui/dialog";
import { FileText, Layout, Zap, CheckCircle, Clock, Edit, AlertTriangle, Loader2, Send, Eye, ChevronsRight } from "lucide-react";
import { toast } from "sonner";
import { getDocumentStatusAPI, listTemplatesAPI, extractDocumentScopeAPI, confirmDocumentScopeAPI, generateTopicsAPI, generateContentAPI, chatWithDocumentAPI, saveDocumentContentAPI } from "@/lib/apiService";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";

interface DocumentStatus {
  status: string;
  message: string;
  pages?: number;
  progress?: number;
}

interface Template {
  project_name: string;
  project_TOC: string;
  file_path?: string;
}

interface ScopeData {
  scope_text: string;
  source_pages: number[];
  is_confirmed: boolean;
  is_complete?: boolean;
}

interface Topic {
  id?: number;
  number?: string;
  text: string;
  level?: number;
  status?: string;
  page?: number;
  is_confirmed?: boolean;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const Analyze = () => {
  const { docId } = useParams<{ docId: string }>();
  const queryClient = useQueryClient();
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [analysisStep, setAnalysisStep] = useState(0);
  const [scopeData, setScopeData] = useState<ScopeData | null>(null);
  const [generatedTopics, setGeneratedTopics] = useState<Topic[]>([]);
  const [generatedContent, setGeneratedContent] = useState<{[topicTextKey: string]: string}>({});
  const [availableTemplates, setAvailableTemplates] = useState<Template[]>([]);
  const [contentLoadingState, setContentLoadingState] = useState<{[topicTextKey: string]: boolean}>({});
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [currentChatMessage, setCurrentChatMessage] = useState("");
  const chatScrollAreaRef = useRef<HTMLDivElement>(null);
  const isBatchGeneratingRef = useRef(false);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentTopicForModal, setCurrentTopicForModal] = useState<Topic | null>(null);
  const [modalContent, setModalContent] = useState("");
  const [isGeneratingAll, setIsGeneratingAll] = useState(false);

  const [isViewAllModalOpen, setIsViewAllModalOpen] = useState(false);
  const [viewAllModalContent, setViewAllModalContent] = useState("");

  const { data: documentStatus, isLoading: isLoadingStatus, error: statusError, refetch: refetchStatus } = useQuery<DocumentStatus, Error, DocumentStatus, readonly string[]>({
    queryKey: ["documentStatus", docId!],
    queryFn: async () => (await getDocumentStatusAPI(docId!)).data,
    enabled: !!docId,
    refetchInterval: (query) => {
      const currentStatus = query.state.data?.status;
      if (currentStatus === "processed" || currentStatus === "error") return false;
      return 5000;
    },
  });

  useEffect(() => {
    if (documentStatus) {
      if (documentStatus.status === "processed") {
        const existingScope = queryClient.getQueryData<ScopeData>(["documentScope", docId]);
        if (existingScope && existingScope.is_confirmed) {
          setScopeData(existingScope);
          setAnalysisStep(3);
        } else if (existingScope) {
          setScopeData(existingScope);
          setAnalysisStep(2);
        } else {
          setAnalysisStep(2);
        }
      } else if (documentStatus.status === "processing" || documentStatus.status === "uploading") {
        setAnalysisStep(1);
      } else {
        setAnalysisStep(0);
      }
    }
  }, [documentStatus, queryClient, docId]);

  const { data: templatesData, isLoading: isLoadingTemplates, error: templatesError } = useQuery<Template[], Error>({
    queryKey: ["templates"],
    queryFn: async () => {
      const response = await listTemplatesAPI();
      const fetchedTemplates = response.data.templates;
      if (typeof fetchedTemplates === 'object' && fetchedTemplates !== null && !Array.isArray(fetchedTemplates)) {
        return Object.entries(fetchedTemplates).map(([projectName, details]) => ({
          project_name: projectName,
          project_TOC: (details as any).project_TOC,
          file_path: (details as any).file_path,
        }));
      }
      return [];
    },
  });

  useEffect(() => {
    if (templatesData) {
      setAvailableTemplates(templatesData || []);
    }
  }, [templatesData]);

  const extractScopeMutation = useMutation<ScopeData, Error, void>({
    mutationFn: async () => (await extractDocumentScopeAPI(docId!, true)).data,
    onSuccess: (data) => {
      toast.success("Scope extracted successfully!");
      setScopeData(data);
      queryClient.setQueryData(["documentScope", docId], data);
    },
    onError: (error) => {
      toast.error(`Failed to extract scope: ${error.message}`);
    },
  });

  const confirmScopeMutation = useMutation<ScopeData, Error, { pages?: number[] } >({
    mutationFn: async (params) => {
        const response = await confirmDocumentScopeAPI(docId!, params.pages || []);
        return response.data.scope;
    },
    onSuccess: (data) => {
      toast.success("Scope confirmed successfully!");
      setScopeData(data);
      queryClient.setQueryData(["documentScope", docId], data);
      setAnalysisStep(3);
    },
    onError: (error) => {
      toast.error(`Failed to confirm scope: ${error.message}`);
    },
  });

  const generateTopicsMutation = useMutation<{topics: Topic[]}, Error, void>({
    mutationFn: async () => (await generateTopicsAPI(docId!, selectedTemplate)).data,
    onSuccess: (data) => {
      toast.success("Topics generated successfully!");
      const newTopics: Topic[] = (data.topics || []).map((topic: any) => ({
        id: topic.id,
        number: topic.number,
        text: topic.text || "Unnamed Topic",
        level: topic.level,
        status: topic.status,
        page: topic.page,
        is_confirmed: topic.is_confirmed
      }));
      setGeneratedTopics(newTopics);
      setAnalysisStep(4);
      queryClient.setQueryData(["generatedTopics", docId, selectedTemplate], newTopics);
    },
    onError: (error) => {
      toast.error(`Failed to generate topics: ${error.message}`);
    },
  });

  const generateContentMutation = useMutation<{content: string, topic: string}, Error, Topic>({
    mutationFn: async (topicToGenerate) => (await generateContentAPI(docId!, selectedTemplate, topicToGenerate.text)).data,
    onMutate: (topicToGenerate) => {
      setContentLoadingState(prev => ({ ...prev, [topicToGenerate.text]: true }));
    },
    onSuccess: (data, topicGenerated) => {
      toast.success(`Content generated for: ${data.topic || topicGenerated.text}`);
      const topicKey = data.topic || topicGenerated.text;
      setGeneratedContent(prev => ({
        ...prev,
        [topicKey]: data.content
      }));
      if (!isBatchGeneratingRef.current) {
        setCurrentTopicForModal(topicGenerated);
        setModalContent(data.content);
        setIsModalOpen(true);
      }
      queryClient.setQueryData(["generatedContent", docId, selectedTemplate, topicKey], data.content);
    },
    onError: (error, topicGenerated) => {
      toast.error(`Failed to generate content for ${topicGenerated.text}: ${error.message}`);
    },
    onSettled: (data, error, topicGenerated) => {
      setContentLoadingState(prev => ({ ...prev, [topicGenerated.text]: false }));
    }
  });

  const saveContentMutation = useMutation<any, Error, { topic: Topic, content: string } >({
    mutationFn: async ({ topic, content }) => {
      if (!docId) {
        toast.error("Cannot save content: Document ID is missing.");
        throw new Error("Document ID is missing");
      }
      if (!topic.id) {
        toast.error("Cannot save content: Topic ID is missing.");
        throw new Error("Topic ID is missing");
      }
      return saveDocumentContentAPI(docId, topic.id, content);
    },
    onSuccess: (data, variables) => {
      toast.success(`Content for "${variables.topic.text}" saved successfully!`);
      setGeneratedContent(prev => ({
        ...prev,
        [variables.topic.text]: variables.content
      }));
    },
    onError: (error, variables) => {
      toast.error(`Failed to save content for "${variables.topic.text}": ${error.message}`);
    },
  });

  const chatMutation = useMutation<{response: string}, Error, { message: string; history: ChatMessage[] } >({
    mutationFn: async ({ message, history }) => (await chatWithDocumentAPI(docId!, selectedTemplate, message, history)).data,
    onMutate: async ({ message }) => {
      setChatHistory(prev => [...prev, { role: "user", content: message }]);
      setCurrentChatMessage("");
    },
    onSuccess: (data) => {
      setChatHistory(prev => [...prev, { role: "assistant", content: data.response }]);
      queryClient.setQueryData(["chatHistory", docId, selectedTemplate], chatHistory);
    },
    onError: (error) => {
      toast.error(`Chat error: ${error.message}`);
      setChatHistory(prev => prev.slice(0, -1));
    },
  });

  useEffect(() => {
    if (docId) {
      console.log("Analyzing document:", docId);
      setAnalysisStep(0);
      setScopeData(null);
      setGeneratedTopics([]);
      setGeneratedContent({});
      setChatHistory([]);
      queryClient.invalidateQueries({ queryKey: ["documentStatus", docId!] });
      queryClient.invalidateQueries({ queryKey: ["documentScope", docId!] });
    } else {
      toast.info("No document selected for analysis. Upload a document or select one.");
    }
  }, [docId, queryClient]);

  useEffect(() => {
    if (docId && selectedTemplate && analysisStep === 3 && scopeData?.is_confirmed) {
        const cachedTopics = queryClient.getQueryData<Topic[]>(["generatedTopics", docId, selectedTemplate]);
        if (cachedTopics) {
            setGeneratedTopics(cachedTopics);
            setAnalysisStep(4);
            const cachedContent: {[key: string]: string} = {};
            cachedTopics.forEach(topic => {
                const content = queryClient.getQueryData<string>(["generatedContent", docId, selectedTemplate, topic.text]);
                if (content) {
                    cachedContent[topic.text] = content;
                }
            });
            setGeneratedContent(cachedContent);
            toast.info("Loaded previously generated topics and content.");
        }
    }
    if (!selectedTemplate && analysisStep >= 3) {
        setGeneratedTopics([]);
        setGeneratedContent({});
        if (scopeData?.is_confirmed) setAnalysisStep(3);
        else if (scopeData) setAnalysisStep(2);
        else setAnalysisStep(0);
    }
  }, [docId, selectedTemplate, analysisStep, scopeData, queryClient]);

  useEffect(() => {
    if (chatScrollAreaRef.current) {
      chatScrollAreaRef.current.scrollTop = chatScrollAreaRef.current.scrollHeight;
    }
  }, [chatHistory]);

  const handleStartAnalysis = async () => {
    if (!docId || !selectedTemplate) {
      toast.error("Document ID is missing or no template selected.");
      return;
    }
    if (documentStatus?.status !== 'processed') {
      toast.error("Document is not yet processed. Please wait.");
      return;
    }
    if (scopeData && !scopeData.is_confirmed) {
        toast.info("Scope already extracted. Please confirm it.");
        setAnalysisStep(2);
        return;
    }
    if (scopeData && scopeData.is_confirmed) {
        toast.info("Scope already confirmed. Proceed to topic generation.");
        setAnalysisStep(3);
        return;
    }
    extractScopeMutation.mutate();
  };

  const handleConfirmScope = () => {
    if (!scopeData) {
      toast.error("No scope data to confirm.");
      return;
    }
    confirmScopeMutation.mutate({});
  };

  const handleGenerateTopics = () => {
    if (!docId || !selectedTemplate) {
      toast.error("Cannot generate topics without a document and selected template.");
      return;
    }
    if (!scopeData || !scopeData.is_confirmed) {
      toast.error("Scope must be confirmed before generating topics.");
      return;
    }
    generateTopicsMutation.mutate();
  };

  const handleGenerateOrViewContent = (topic: Topic) => {
    const content = generatedContent[topic.text];
    if (content) {
      setCurrentTopicForModal(topic);
      setModalContent(content);
      setIsModalOpen(true);
    } else {
      if (generateContentMutation.isPending && contentLoadingState[topic.text]) {
        toast.info(`Still generating content for: ${topic.text}`);
        return;
      }
      if (generateContentMutation.isPending && !contentLoadingState[topic.text]) {
        toast.info("Please wait for the current content generation to complete.");
        return;
      }
      generateContentMutation.mutate(topic);
    }
  };

  const handleGenerateAllContent = async () => {
    if (!generatedTopics.length) {
      toast.info("No topics available to generate content for.");
      return;
    }
    isBatchGeneratingRef.current = true;
    setIsGeneratingAll(true);
    toast.info("Starting batch content generation...");
    let count = 0;
    for (const topic of generatedTopics) {
      if (!generatedContent[topic.text] && !contentLoadingState[topic.text]) {
        try {
          await generateContentMutation.mutateAsync(topic);
          count++;
        } catch (error) {
          toast.error(`Failed to generate content for ${topic.text} during batch operation.`);
        }
      }
    }
    isBatchGeneratingRef.current = false;
    setIsGeneratingAll(false);
    if(count > 0) toast.success(`Batch content generation completed for ${count} topics.`);
    else toast.info("No new content was generated in batch (already exists or was generating).");
  };

  const handleOpenViewAllModal = () => {
    if (generatedTopics.length === 0) {
      toast.info("No topics available to display.");
      return;
    }
    let allContent = "";
    let generatedCount = 0;
    generatedTopics.forEach(topic => {
      const content = generatedContent[topic.text];
      if (content) {
        allContent += `## ${topic.number ? topic.number + ". " : ""}${topic.text}\n\n${content}\n\n---\n\n`;
        generatedCount++;
      }
    });

    if (generatedCount === 0) {
      toast.info("No content has been generated yet for any topic.");
      return;
    }

    setViewAllModalContent(allContent.trim());
    setIsViewAllModalOpen(true);
  };

  const handleSaveModalContent = () => {
    if (currentTopicForModal && docId) {
      setGeneratedContent(prev => ({
        ...prev,
        [currentTopicForModal.text]: modalContent
      }));
      queryClient.setQueryData(["generatedContent", docId, selectedTemplate, currentTopicForModal.text], modalContent);
      if (currentTopicForModal.id) {
        saveContentMutation.mutate({ topic: currentTopicForModal, content: modalContent });
      } else {
        toast.info("Content saved locally. Topic ID missing for backend save.");
      }
      setIsModalOpen(false);
    } else {
      toast.error("Error saving content: No topic selected or document ID missing.")
    }
  };

  const handleSendChatMessage = () => {
    if (!currentChatMessage.trim()) return;
    if (!docId || !selectedTemplate) {
      toast.error("Document and template must be selected for chat.");
      return;
    }
    const historyForAPI = chatHistory.map(msg => ({ role: msg.role, content: msg.content }));
    chatMutation.mutate({ message: currentChatMessage, history: historyForAPI });
  };

  const getStepStatusDisplay = (step: number) => {
    if (documentStatus?.status === "error") return "error";

    if (step === 1) {
      if (extractScopeMutation.isPending || generateTopicsMutation.isPending) return "pending";
      if (documentStatus?.status === "uploading" || documentStatus?.status === "processing") return "current";
      if (documentStatus?.status === "processed" || analysisStep >= 2) return "complete";
      return "pending";
    }
    if (step === 2) {
      if (documentStatus?.status !== "processed") return "pending";
      if (generateTopicsMutation.isPending) return "pending";
      if (extractScopeMutation.isPending) return "current";
      if (scopeData && !scopeData.is_confirmed && !confirmScopeMutation.isPending) return "current";
      if (confirmScopeMutation.isPending) return "current";
      if (scopeData && scopeData.is_confirmed || analysisStep >=3) return "complete";
      return "pending";
    }
    if (step === 3) {
       if (!(scopeData && scopeData.is_confirmed)) return "pending";
       if (generateTopicsMutation.isPending) return "current";
       if (analysisStep === 3 && generatedTopics.length === 0 && !generateTopicsMutation.isPending) return "current";
       if (analysisStep >= 4 || (analysisStep === 3 && generatedTopics.length > 0)) return "complete";
       return "pending";
    }
    if (step === 4) {
        if (analysisStep === 4 && generatedTopics.length > 0) return "complete";
        return "pending";
    }
    return "pending";
  };

  if (!docId) {
    return (
      <div className="container mx-auto px-6 py-8 text-center">
        <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold mb-2">No Document Selected</h3>
        <p className="text-gray-600">Please upload a document or select one from the dashboard to start analysis.</p>
      </div>
    );
  }

  if (isLoadingStatus && !documentStatus) {
    return <div className="flex justify-center items-center h-screen"><Clock className="w-12 h-12 animate-spin text-blue-600" /> <p className="ml-4 text-xl">Loading document status...</p></div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Analyze Document: {docId}</h1>
          {documentStatus && (
            <div className="mt-2">
              <Badge variant={documentStatus.status === "processed" ? "default" : documentStatus.status === "error" ? "destructive" : "secondary"}
                     className={`${documentStatus.status === "processed" ? "bg-green-500 text-white" : ""} ${documentStatus.status === "error" ? "bg-red-500 text-white" : ""}`}>
                Status: {documentStatus.status}
              </Badge>
              {documentStatus.message && <p className="text-sm text-gray-600 mt-1">{documentStatus.message}</p>}
              {documentStatus.status === "processing" && typeof documentStatus.progress === 'number' && (
                <div className="mt-2">
                  <Progress value={documentStatus.progress} className="w-full" />
                  <p className="text-xs text-gray-500 text-right">{documentStatus.progress}% complete</p>
                </div>
              )}
            </div>
          )}
           {statusError && <p className="text-red-500 mt-2">Error fetching status: {statusError.message}</p>}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Configuration</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Selected Document</label>
                  <Input type="text" readOnly value={docId || "N/A"} className="bg-gray-100" />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Select Template</label>
                  <select 
                    className="w-full p-2 border rounded-md"
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                    disabled={isLoadingTemplates || availableTemplates.length === 0 || analysisStep > 3}
                  >
                    <option value="">{isLoadingTemplates ? "Loading templates..." : "Choose a template..."}</option>
                    {availableTemplates.map((template) => (
                      <option key={template.project_name} value={template.project_name}>{template.project_name}</option>
                    ))}
                  </select>
                  {templatesError && <p className="text-xs text-red-500 mt-1">Error loading templates.</p>}
                </div>

                <Button 
                  className="w-full"
                  onClick={handleStartAnalysis}
                  disabled={ 
                    !docId || 
                    !selectedTemplate || 
                    documentStatus?.status !== 'processed' || 
                    extractScopeMutation.isPending ||
                    (scopeData != null && scopeData.is_confirmed)
                  }
                >
                  {extractScopeMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Zap className="w-4 h-4 mr-2" />}
                  {scopeData && !scopeData.is_confirmed ? "Scope Extracted (Confirm Below)" 
                    : scopeData && scopeData.is_confirmed ? "Scope Confirmed"
                    : "Start Scope Extraction"}
                </Button>
              </CardContent>
            </Card>

            {(docId && (documentStatus?.status !== "error" || analysisStep > 0)) && (
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle>Analysis Pipeline</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      {getStepStatusDisplay(1) === "complete" ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : getStepStatusDisplay(1) === "current" ? (
                        <Clock className="w-5 h-5 text-blue-500 animate-spin" />
                      ) : getStepStatusDisplay(1) === "error" ? (
                        <AlertTriangle className="w-5 h-5 text-red-500" />
                      ) : (
                        <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
                      )}
                      <span className={`${getStepStatusDisplay(1) === "complete" ? "text-green-700" : getStepStatusDisplay(1) === "error" ? "text-red-700 line-through" : ""}`}>
                        Document Processing
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                     {getStepStatusDisplay(2) === "complete" ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : getStepStatusDisplay(2) === "current" ? (
                        <Clock className="w-5 h-5 text-blue-500 animate-spin" />
                      ) : (
                        <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
                      )}
                      <span className={getStepStatusDisplay(2) === "complete" ? "text-green-700" : ""}>
                        Scope Extraction & Confirmation
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      {getStepStatusDisplay(3) === "complete" ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : getStepStatusDisplay(3) === "current" ? (
                        <Clock className="w-5 h-5 text-blue-500 animate-spin" />
                      ) : (
                        <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
                      )}
                      <span className={getStepStatusDisplay(3) === "complete" ? "text-green-700" : ""}>
                        Topic Generation
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      {getStepStatusDisplay(4) === "complete" ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : (
                        <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
                      )}
                      <span className={getStepStatusDisplay(4) === "complete" ? "text-green-700" : ""}>
                        Content Generation Ready
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          <div className="lg:col-span-2">
            {(!docId || (documentStatus && documentStatus.status !== 'processed' && analysisStep < 2 && !scopeData) ) && (
              <Card>
                <CardContent className="p-12 text-center">
                  <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold mb-2">
                    {docId ? (isLoadingStatus && !documentStatus ? "Loading Document Info..." : `Processing Document: ${docId}`) : "No Document Active"}
                  </h3>
                  <p className="text-gray-600">
                    {isLoadingStatus && !documentStatus ? "Fetching status..." : documentStatus?.message || "Please wait for document processing to complete or select a document."}
                  </p>
                  {documentStatus?.status === "processing" && typeof documentStatus.progress === 'number' && (
                     <Progress value={documentStatus.progress} className="w-1/2 mx-auto mt-4" />
                  )}
                </CardContent>
              </Card>
            )}

            {docId && (documentStatus?.status === 'processed' || scopeData) && analysisStep === 2 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex justify-between items-center">
                    Scope Details
                    {scopeData && !scopeData.is_confirmed && (
                      <Badge variant="default" className="bg-yellow-400 text-yellow-900">Awaiting Confirmation</Badge>
                    )}
                    {scopeData && scopeData.is_confirmed && (
                      <Badge variant="default" className="bg-green-500 text-white">Scope Confirmed</Badge>
                    )}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {extractScopeMutation.isPending && (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 className="w-8 h-8 mr-2 animate-spin" /> Fetching scope...
                    </div>
                  )}
                  {extractScopeMutation.error && (
                    <p className="text-red-500">Error extracting scope: {extractScopeMutation.error.message}</p>
                  )}
                  {scopeData && (
                    <div>
                      <h4 className="font-semibold mb-2">Extracted Scope Text:</h4>
                      <Textarea readOnly value={scopeData.scope_text} className="min-h-[150px] bg-gray-50 mb-4" />
                      <h4 className="font-semibold mb-1">Source Pages:</h4>
                      <p className="text-sm text-gray-700 mb-4">
                        {scopeData.source_pages && scopeData.source_pages.length > 0 ? scopeData.source_pages.join(", ") : "N/A"}
                      </p>
                      {!scopeData.is_confirmed && (
                        <Button 
                          onClick={handleConfirmScope} 
                          disabled={confirmScopeMutation.isPending}
                          className="w-full"
                        >
                          {confirmScopeMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                          Confirm Scope
                        </Button>
                      )}
                      {confirmScopeMutation.error && (
                        <p className="text-red-500 mt-2">Error confirming scope: {confirmScopeMutation.error.message}</p>
                      )}
                    </div>
                  )}
                  {!extractScopeMutation.isPending && !scopeData && !extractScopeMutation.error && !isLoadingStatus && (
                     <p>Select a template and click "Start Scope Extraction" in the configuration panel to begin.</p>
                  )}
                </CardContent>
              </Card>
            )}
            
            {docId && analysisStep === 3 && scopeData?.is_confirmed && (
                 <Card>
                    <CardHeader><CardTitle>Topic Generation</CardTitle></CardHeader>
                    <CardContent className="text-center py-6">
                        {generateTopicsMutation.isPending ? (
                            <div className="flex flex-col items-center gap-2">
                                <Loader2 className="w-8 h-8 mr-2 animate-spin" />
                                <p>Generating topics based on '{selectedTemplate}'...</p>
                            </div>
                        ) : generatedTopics.length > 0 ? (
                            <p className="text-green-600">Topics generated. See below to generate content.</p>
                        ) : (
                            <Button onClick={handleGenerateTopics} disabled={!selectedTemplate || generateTopicsMutation.isPending || !scopeData?.is_confirmed}>
                                <Zap className="w-4 h-4 mr-2" /> Generate Topics with '{selectedTemplate}'
                            </Button>
                        )}
                        {generateTopicsMutation.error && (
                            <p className="text-red-500 mt-2">Error: {generateTopicsMutation.error.message}</p>
                        )}
                    </CardContent>
                </Card>
            )}

            {docId && analysisStep >= 4 && generatedTopics.length > 0 && (
              <div className="space-y-6 mt-0">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex justify-between items-center">
                        Generated Topics
                        <Button 
                            size="sm" 
                            variant="outline"
                            onClick={handleGenerateAllContent}
                            disabled={isGeneratingAll || generatedTopics.every(t => !!generatedContent[t.text] || contentLoadingState[t.text])}
                        >
                            {isGeneratingAll ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ChevronsRight className="mr-2 h-4 w-4" />}
                            Generate All Content
                        </Button>
                        <Button 
                            size="sm" 
                            variant="outline"
                            onClick={handleOpenViewAllModal}
                            disabled={isGeneratingAll || generatedTopics.length === 0 || Object.keys(generatedContent).length === 0}
                            className="ml-2"
                        >
                            <Eye className="mr-2 h-4 w-4" /> 
                            View All Content
                        </Button>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {generatedTopics.map((topic) => (
                        <div key={topic.id || topic.text} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <span className="font-medium truncate pr-2" title={topic.text}>{topic.number ? `${topic.number}. ` : ""}{topic.text}</span>
                          <Button 
                            size="sm" 
                            onClick={() => handleGenerateOrViewContent(topic)}
                            disabled={(isGeneratingAll && !generatedContent[topic.text]) || (contentLoadingState[topic.text]) || (generateContentMutation.isPending && !contentLoadingState[topic.text] && !isGeneratingAll)}
                          >
                            {contentLoadingState[topic.text] ? (
                              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating...</>
                            ) : generatedContent[topic.text] ? (
                              <><Eye className="mr-2 h-4 w-4" /> View</>
                            ) : (
                              "Generate"
                            )}
                          </Button>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
            
            {docId && analysisStep >= 4 && selectedTemplate && generatedTopics.length > 0 && (
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle>Chat with Document: {docId} (using '{selectedTemplate}' context)</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[450px] w-full border rounded-md p-4 mb-4" ref={chatScrollAreaRef}>
                    {chatHistory.map((msg, index) => (
                      <div key={index} className={`mb-3 p-3 rounded-lg max-w-[80%] ${ 
                        msg.role === 'user' ? 'bg-blue-500 text-white ml-auto' : 'bg-gray-200 text-gray-800 mr-auto'
                      }`}>
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                      </div>
                    ))}
                    {chatMutation.isPending && (
                        <div className="mb-3 p-3 rounded-lg max-w-[80%] bg-gray-200 text-gray-800 mr-auto animate-pulse">
                            <p className="text-sm">Assistant is typing...</p>
                        </div>
                    )}
                  </ScrollArea>
                  <div className="flex gap-2">
                    <Input 
                      type="text"
                      placeholder="Ask a question about the document..."
                      value={currentChatMessage}
                      onChange={(e) => setCurrentChatMessage(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && !chatMutation.isPending && handleSendChatMessage()}
                      disabled={chatMutation.isPending}
                    />
                    <Button onClick={handleSendChatMessage} disabled={chatMutation.isPending || !currentChatMessage.trim()}>
                      {chatMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    </Button>
                  </div>
                  {chatMutation.error && (
                    <p className="text-red-500 text-sm mt-2">Chat error: {chatMutation.error.message}</p>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
          <DialogContent className="sm:max-w-2xl md:max-w-3xl lg:max-w-4xl max-h-[90vh] flex flex-col">
            <DialogHeader>
              <DialogTitle>Content: {currentTopicForModal?.number ? `${currentTopicForModal.number} ` : ""}{currentTopicForModal?.text}</DialogTitle>
            </DialogHeader>
            <div className="flex-grow overflow-y-auto py-4 pr-2">
                <Textarea 
                    value={modalContent}
                    onChange={(e) => setModalContent(e.target.value)}
                    className="min-h-[400px] w-full font-mono text-sm"
                    placeholder="Content will appear here..."
                />
            </div>
            <DialogFooter className="mt-auto pt-4">
              <DialogClose asChild>
                <Button variant="outline">Close</Button>
              </DialogClose>
              <Button onClick={handleSaveModalContent} disabled={saveContentMutation.isPending || !currentTopicForModal}>
                {saveContentMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin"/> : null}
                Save Content
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Modal for Viewing All Content */}
        <Dialog open={isViewAllModalOpen} onOpenChange={setIsViewAllModalOpen}>
          <DialogContent className="sm:max-w-2xl md:max-w-3xl lg:max-w-4xl max-h-[90vh] flex flex-col">
            <DialogHeader>
              <DialogTitle>All Generated Content for: {docId}</DialogTitle>
            </DialogHeader>
            <ScrollArea className="flex-grow py-4 pr-2 border rounded-md my-2">
                <Textarea 
                    value={viewAllModalContent}
                    readOnly
                    className="min-h-[500px] w-full font-mono text-sm bg-gray-50 whitespace-pre-wrap"
                    placeholder="Consolidated content will appear here..."
                />
            </ScrollArea>
            <DialogFooter className="mt-auto pt-4">
              <DialogClose asChild>
                <Button variant="outline">Close</Button>
              </DialogClose>
            </DialogFooter>
          </DialogContent>
        </Dialog>

      </div>
    </div>
  );
};

export default Analyze;
