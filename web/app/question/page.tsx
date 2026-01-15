"use client";

import { useState, useEffect } from "react";
import {
  PenTool,
  Loader2,
  RefreshCw,
  Database,
  Activity,
  CheckCircle2,
  BrainCircuit,
  FileText,
  Upload,
  Sparkles,
  Book,
  Zap,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Lightbulb,
} from "lucide-react";
import { useGlobal } from "@/context/GlobalContext";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { apiUrl } from "@/lib/api";
import { processLatexContent } from "@/lib/latex";
import AddToNotebookModal from "@/components/AddToNotebookModal";
import { LogDrawer } from "@/components/question";
import { useQuestionReducer } from "@/hooks/useQuestionReducer";

export default function QuestionPage() {
  const {
    questionState,
    setQuestionState,
    startQuestionGen,
    startMimicQuestionGen,
    resetQuestionGen,
  } = useGlobal();

  // Dashboard state for parallel generation
  const [dashboardState, dispatchDashboard] = useQuestionReducer();

  // UI state
  const [activeIdx, setActiveIdx] = useState(0);
  const [userAnswers, setUserAnswers] = useState<Record<number, string>>({});
  const [submittedMap, setSubmittedMap] = useState<Record<number, boolean>>({});
  const [kbs, setKbs] = useState<string[]>([]);
  const [showLogDrawer, setShowLogDrawer] = useState(false);
  const [showNotebookModal, setShowNotebookModal] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);

  // Derived state
  const isGenerating = questionState.step === "generating";
  const isComplete = questionState.step === "result";
  const isConfigMode = questionState.step === "config";
  const totalQuestions = questionState.results.length;
  const currentQuestion = questionState.results[activeIdx];
  const extendedCount = questionState.results.filter(
    (r: any) => r.extended,
  ).length;

  // Progress info from questionState
  const progress = questionState.progress || {};
  const stage =
    progress.stage ||
    (isGenerating ? "generating" : isComplete ? "complete" : null);
  const subFocuses = progress.subFocuses || [];

  // Fetch KBs on mount
  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    fetch(apiUrl("/api/v1/knowledge/list"), { signal: controller.signal })
      .then((res) => res.json())
      .then((data) => {
        if (!isMounted) return;
        const names = data.map((kb: any) => kb.name);
        setKbs(names);
        if (!questionState.selectedKb && names.length > 0) {
          setQuestionState((prev) => ({ ...prev, selectedKb: names[0] }));
        }
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          console.error("Failed to fetch KBs:", err);
        }
      });

    return () => {
      isMounted = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-select first question when results come in
  useEffect(() => {
    if (
      questionState.results.length > 0 &&
      activeIdx >= questionState.results.length
    ) {
      setActiveIdx(0);
    }
  }, [questionState.results.length, activeIdx]);

  const handleStart = () => {
    if (questionState.mode === "knowledge") {
      startQuestionGen(
        questionState.topic,
        questionState.difficulty,
        questionState.type,
        questionState.count,
        questionState.selectedKb,
      );
    } else {
      // Mimic mode: don't limit questions by default (process all reference questions)
      // Only limit if user explicitly sets a value via maxQuestions state
      startMimicQuestionGen(
        questionState.uploadedFile,
        questionState.paperPath,
        questionState.selectedKb,
        undefined, // Let backend process all reference questions
      );
    }
    setUserAnswers({});
    setSubmittedMap({});
    setActiveIdx(0);
  };

  const handleAnswer = (val: string) => {
    if (submittedMap[activeIdx]) return;
    setUserAnswers((prev) => ({ ...prev, [activeIdx]: val }));
  };

  const handleSubmit = () => {
    setSubmittedMap((prev) => ({ ...prev, [activeIdx]: true }));
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    if (file && file.type !== "application/pdf") {
      alert("Please upload a PDF exam paper");
      return;
    }
    setQuestionState((prev) => ({
      ...prev,
      uploadedFile: file,
      paperPath: file ? "" : prev.paperPath,
    }));
  };

  const handleReset = () => {
    resetQuestionGen();
    setUserAnswers({});
    setSubmittedMap({});
    setActiveIdx(0);
  };

  const canStart =
    questionState.mode === "knowledge"
      ? questionState.topic.trim().length > 0
      : questionState.uploadedFile !== null ||
        questionState.paperPath.trim().length > 0;

  return (
    <div className="h-screen flex gap-0 p-4 animate-fade-in overflow-hidden">
      {/* Main Panel */}
      <div className="flex-1 flex flex-col bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex justify-between items-center backdrop-blur-sm shrink-0">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200 font-semibold">
              <PenTool className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              Question Generator
            </div>

            {/* Mode Switching */}
            {isConfigMode && (
              <div className="flex bg-slate-100 dark:bg-slate-700 p-1 rounded-lg border border-slate-200 dark:border-slate-600">
                <button
                  onClick={() =>
                    setQuestionState((prev) => ({ ...prev, mode: "knowledge" }))
                  }
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                    questionState.mode === "knowledge"
                      ? "bg-white dark:bg-slate-600 text-purple-700 dark:text-purple-400 shadow-sm"
                      : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                  }`}
                >
                  <BrainCircuit className="w-4 h-4" />
                  Custom
                </button>
                <button
                  onClick={() =>
                    setQuestionState((prev) => ({ ...prev, mode: "mimic" }))
                  }
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                    questionState.mode === "mimic"
                      ? "bg-white dark:bg-slate-600 text-purple-700 dark:text-purple-400 shadow-sm"
                      : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                  }`}
                >
                  <FileText className="w-4 h-4" />
                  Mimic Exam
                </button>
              </div>
            )}

            {/* Status indicator when generating/complete */}
            {!isConfigMode && (
              <div className="flex items-center gap-2 text-sm">
                {isGenerating ? (
                  <div className="flex items-center gap-2 px-3 py-1 bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded-full">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>
                      Generating {totalQuestions}/{questionState.count}...
                    </span>
                  </div>
                ) : isComplete ? (
                  <div className="flex items-center gap-2 px-3 py-1 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-full">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{totalQuestions} questions</span>
                    {extendedCount > 0 && (
                      <span className="text-amber-600 dark:text-amber-400">
                        ({extendedCount} extended)
                      </span>
                    )}
                  </div>
                ) : null}
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Knowledge Base selector */}
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-slate-400 dark:text-slate-500" />
              <select
                value={questionState.selectedKb}
                onChange={(e) =>
                  setQuestionState((prev) => ({
                    ...prev,
                    selectedKb: e.target.value,
                  }))
                }
                disabled={isGenerating}
                className="text-sm bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 outline-none focus:border-purple-400 dark:text-slate-200 disabled:opacity-50"
              >
                {kbs.map((kb) => (
                  <option key={kb} value={kb}>
                    {kb}
                  </option>
                ))}
              </select>
            </div>

            {/* Log Drawer Toggle */}
            {!isConfigMode && (
              <button
                onClick={() => setShowLogDrawer(true)}
                className="flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400 hover:text-purple-600 dark:hover:text-purple-400 px-3 py-1.5 hover:bg-purple-50 dark:hover:bg-purple-900/30 rounded-lg transition-colors"
              >
                <Activity className="w-4 h-4" />
                Logs
              </button>
            )}

            {/* New/Reset button */}
            {!isConfigMode && (
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400 hover:text-purple-600 dark:hover:text-purple-400 px-3 py-1.5 hover:bg-purple-50 dark:hover:bg-purple-900/30 rounded-lg border border-slate-200 dark:border-slate-600 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                New
              </button>
            )}
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto bg-slate-50/30 dark:bg-slate-900/30">
          {/* Config Mode */}
          {isConfigMode && (
            <div className="p-6">
              <div className="max-w-2xl mx-auto space-y-6">
                {/* Mode Info Banner */}
                <div
                  className={`p-4 rounded-xl border ${
                    questionState.mode === "knowledge"
                      ? "bg-purple-50 dark:bg-purple-900/30 border-purple-200 dark:border-purple-800"
                      : "bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {questionState.mode === "knowledge" ? (
                      <BrainCircuit className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                    ) : (
                      <FileText className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                    )}
                    <div>
                      <h3
                        className={`font-semibold ${
                          questionState.mode === "knowledge"
                            ? "text-purple-800 dark:text-purple-300"
                            : "text-blue-800 dark:text-blue-300"
                        }`}
                      >
                        {questionState.mode === "knowledge"
                          ? "Custom Mode"
                          : "Mimic Exam Paper Mode"}
                      </h3>
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        {questionState.mode === "knowledge"
                          ? "Generate questions based on knowledge base content"
                          : "Generate similar questions based on an exam paper"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Knowledge Base Mode Config */}
                {questionState.mode === "knowledge" && (
                  <>
                    <div className="space-y-2">
                      <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Knowledge Point / Topic
                      </label>
                      <input
                        type="text"
                        value={questionState.topic}
                        onChange={(e) =>
                          setQuestionState((prev) => ({
                            ...prev,
                            topic: e.target.value,
                          }))
                        }
                        placeholder="e.g. Gradient Descent Optimization"
                        className="w-full p-4 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/10 transition-all text-lg dark:text-slate-200 placeholder:text-slate-400"
                      />
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                          Count
                        </label>
                        <input
                          type="number"
                          min="1"
                          max="50"
                          value={questionState.count || ""}
                          onChange={(e) => {
                            const rawVal = e.target.value;
                            // Allow empty input while typing
                            if (rawVal === "") {
                              setQuestionState((prev) => ({
                                ...prev,
                                count: 0,
                              }));
                              return;
                            }
                            const val = parseInt(rawVal);
                            if (!isNaN(val)) {
                              setQuestionState((prev) => ({
                                ...prev,
                                count: Math.min(50, Math.max(0, val)),
                              }));
                            }
                          }}
                          onBlur={(e) => {
                            // Ensure valid value on blur
                            const val = parseInt(e.target.value) || 1;
                            setQuestionState((prev) => ({
                              ...prev,
                              count: Math.max(1, Math.min(50, val)),
                            }));
                          }}
                          className="w-full p-3 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-center outline-none focus:border-purple-500 dark:text-slate-200"
                        />
                      </div>

                      <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                          Difficulty
                        </label>
                        <select
                          value={questionState.difficulty}
                          onChange={(e) =>
                            setQuestionState((prev) => ({
                              ...prev,
                              difficulty: e.target.value,
                            }))
                          }
                          className="w-full p-3 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl outline-none focus:border-purple-500 dark:text-slate-200"
                        >
                          <option value="easy">Easy</option>
                          <option value="medium">Medium</option>
                          <option value="hard">Hard</option>
                        </select>
                      </div>

                      <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                          Type
                        </label>
                        <select
                          value={questionState.type}
                          onChange={(e) =>
                            setQuestionState((prev) => ({
                              ...prev,
                              type: e.target.value,
                            }))
                          }
                          className="w-full p-3 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl outline-none focus:border-purple-500 dark:text-slate-200"
                        >
                          <option value="choice">Multiple Choice</option>
                          <option value="written">Written</option>
                        </select>
                      </div>
                    </div>
                  </>
                )}

                {/* Mimic Mode Config */}
                {questionState.mode === "mimic" && (
                  <div className="space-y-5">
                    <div className="space-y-2">
                      <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Upload Exam Paper (PDF)
                      </label>
                      <div className="relative">
                        <input
                          type="file"
                          accept=".pdf"
                          onChange={handleFileUpload}
                          className="hidden"
                          id="pdf-upload"
                        />
                        <label
                          htmlFor="pdf-upload"
                          className="flex items-center justify-center gap-3 w-full py-8 border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-xl cursor-pointer hover:border-purple-400 dark:hover:border-purple-500 hover:bg-purple-50/50 dark:hover:bg-purple-900/20 transition-all"
                        >
                          {questionState.uploadedFile ? (
                            <div className="flex items-center gap-3 text-purple-700 dark:text-purple-400">
                              <FileText className="w-8 h-8" />
                              <div>
                                <p className="font-medium">
                                  {questionState.uploadedFile.name}
                                </p>
                                <p className="text-xs text-slate-500 dark:text-slate-400">
                                  {(
                                    questionState.uploadedFile.size /
                                    1024 /
                                    1024
                                  ).toFixed(2)}{" "}
                                  MB
                                </p>
                              </div>
                            </div>
                          ) : (
                            <div className="text-center text-slate-500 dark:text-slate-400">
                              <Upload className="w-8 h-8 mx-auto mb-2 text-slate-400" />
                              <p className="font-medium">Click to upload PDF</p>
                              <p className="text-xs">
                                The system will parse and generate questions
                              </p>
                            </div>
                          )}
                        </label>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-px bg-slate-200 dark:bg-slate-600"></div>
                      <span className="text-xs text-slate-400 dark:text-slate-500">
                        OR
                      </span>
                      <div className="flex-1 h-px bg-slate-200 dark:bg-slate-600"></div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Pre-parsed Directory
                      </label>
                      <input
                        type="text"
                        value={questionState.paperPath}
                        onChange={(e) =>
                          setQuestionState((prev) => ({
                            ...prev,
                            paperPath: e.target.value,
                            uploadedFile: null,
                          }))
                        }
                        placeholder="e.g. 2211asm1"
                        className="w-full p-3 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl outline-none focus:border-purple-500 dark:text-slate-200 placeholder:text-slate-400"
                      />
                    </div>
                  </div>
                )}

                {/* Generate Button */}
                <button
                  onClick={handleStart}
                  disabled={!canStart || isGenerating}
                  className="w-full py-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl font-bold text-lg shadow-lg shadow-purple-500/30 hover:from-purple-700 hover:to-indigo-700 hover:shadow-purple-500/50 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  <Sparkles className="w-5 h-5" />
                  Generate Questions
                </button>
              </div>
            </div>
          )}

          {/* Question Display Mode */}
          {!isConfigMode && (
            <div className="flex h-full">
              {/* Left: Question List */}
              <div className="w-72 flex-shrink-0 border-r border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800 flex flex-col">
                <div className="p-3 border-b border-slate-100 dark:border-slate-700">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Questions
                    </span>
                    <span className="text-xs text-slate-400">
                      {totalQuestions}/{questionState.count}
                    </span>
                  </div>
                  {isGenerating && questionState.count > 0 && (
                    <div className="mt-2 h-1 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 transition-all duration-300"
                        style={{
                          width: `${(totalQuestions / questionState.count) * 100}%`,
                        }}
                      />
                    </div>
                  )}
                </div>
                <div className="flex-1 overflow-y-auto p-2">
                  {totalQuestions === 0 && isGenerating && (
                    <div className="flex flex-col items-center justify-center h-full text-slate-400">
                      <Loader2 className="w-8 h-8 animate-spin mb-2" />
                      <p className="text-sm">Generating...</p>
                    </div>
                  )}
                  {questionState.results.map((result: any, idx: number) => (
                    <button
                      key={idx}
                      onClick={() => setActiveIdx(idx)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg transition-all mb-1 ${
                        activeIdx === idx
                          ? "bg-purple-50 dark:bg-purple-900/30 border-l-2 border-purple-500"
                          : "hover:bg-slate-50 dark:hover:bg-slate-700"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                            result.extended
                              ? "bg-amber-100 dark:bg-amber-900/40 text-amber-600"
                              : submittedMap[idx]
                                ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600"
                                : activeIdx === idx
                                  ? "bg-purple-100 dark:bg-purple-900/40 text-purple-600"
                                  : "bg-slate-100 dark:bg-slate-700 text-slate-500"
                          }`}
                        >
                          {result.extended ? (
                            <Zap className="w-3.5 h-3.5" />
                          ) : submittedMap[idx] ? (
                            <CheckCircle2 className="w-3.5 h-3.5" />
                          ) : (
                            idx + 1
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p
                            className={`text-sm line-clamp-2 ${activeIdx === idx ? "text-slate-800 dark:text-slate-100 font-medium" : "text-slate-600 dark:text-slate-300"}`}
                          >
                            {result.question.question.slice(0, 80)}...
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-slate-400 uppercase">
                              {result.question.type ||
                                result.question.question_type}
                            </span>
                            {result.extended && (
                              <span className="text-xs text-amber-500">
                                Extended
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Right: Question Detail */}
              <div className="flex-1 flex flex-col overflow-hidden">
                {currentQuestion ? (
                  <>
                    {/* Question Header */}
                    <div className="px-6 py-3 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between bg-white dark:bg-slate-800">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-slate-500">
                          Question {activeIdx + 1}
                        </span>
                        <span className="px-2 py-0.5 text-xs font-bold uppercase tracking-wider bg-slate-100 dark:bg-slate-700 text-slate-500 rounded">
                          {currentQuestion.question.type ||
                            currentQuestion.question.question_type}
                        </span>
                        {currentQuestion.extended && (
                          <span className="px-2 py-0.5 text-xs font-bold uppercase tracking-wider bg-amber-100 dark:bg-amber-900/40 text-amber-600 rounded flex items-center gap-1">
                            <Zap className="w-3 h-3" />
                            Extended
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => setShowNotebookModal(true)}
                        className="text-xs text-indigo-500 hover:text-indigo-600 flex items-center gap-1 px-2 py-1 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded-lg transition-colors"
                      >
                        <Book className="w-3 h-3" />
                        Add to Notebook
                      </button>
                    </div>

                    {/* Question Content */}
                    <div className="flex-1 overflow-y-auto p-6 space-y-6">
                      {/* Question Text */}
                      <div className="prose prose-slate dark:prose-invert max-w-none">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm, remarkMath]}
                          rehypePlugins={[rehypeKatex]}
                        >
                          {processLatexContent(
                            currentQuestion.question.question,
                          )}
                        </ReactMarkdown>
                      </div>

                      {/* Options or Input */}
                      {(currentQuestion.question.question_type === "choice" ||
                        currentQuestion.question.type === "choice") &&
                      currentQuestion.question.options &&
                      Object.keys(currentQuestion.question.options).length >
                        0 ? (
                        <div className="space-y-3">
                          {Object.entries(currentQuestion.question.options).map(
                            ([key, val]) => {
                              const isSelected = userAnswers[activeIdx] === key;
                              const isCorrect =
                                key === currentQuestion.question.correct_answer;
                              const showCorrectness = submittedMap[activeIdx];

                              return (
                                <button
                                  key={key}
                                  onClick={() =>
                                    !submittedMap[activeIdx] &&
                                    handleAnswer(key)
                                  }
                                  disabled={submittedMap[activeIdx]}
                                  className={`w-full text-left p-4 rounded-xl border transition-all flex items-start gap-4 prose dark:prose-invert max-w-none ${
                                    showCorrectness
                                      ? isCorrect
                                        ? "bg-emerald-50 dark:bg-emerald-900/30 border-emerald-300"
                                        : isSelected
                                          ? "bg-red-50 dark:bg-red-900/30 border-red-300"
                                          : "bg-white dark:bg-slate-700 border-slate-200 dark:border-slate-600"
                                      : isSelected
                                        ? "bg-purple-50 dark:bg-purple-900/30 border-purple-300"
                                        : "bg-white dark:bg-slate-700 border-slate-200 dark:border-slate-600 hover:border-purple-300"
                                  }`}
                                >
                                  <span
                                    className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold ${
                                      showCorrectness && isCorrect
                                        ? "bg-emerald-500 text-white"
                                        : showCorrectness &&
                                            isSelected &&
                                            !isCorrect
                                          ? "bg-red-500 text-white"
                                          : isSelected
                                            ? "bg-purple-500 text-white"
                                            : "bg-slate-100 dark:bg-slate-600 text-slate-600 dark:text-slate-300"
                                    }`}
                                  >
                                    {key}
                                  </span>
                                  <div className="flex-1">
                                    <ReactMarkdown
                                      remarkPlugins={[remarkGfm, remarkMath]}
                                      rehypePlugins={[rehypeKatex]}
                                    >
                                      {processLatexContent(String(val))}
                                    </ReactMarkdown>
                                  </div>
                                  {showCorrectness && isCorrect && (
                                    <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                                  )}
                                </button>
                              );
                            },
                          )}
                        </div>
                      ) : (
                        <textarea
                          value={userAnswers[activeIdx] || ""}
                          onChange={(e) => handleAnswer(e.target.value)}
                          disabled={submittedMap[activeIdx]}
                          placeholder="Type your answer here..."
                          className="w-full h-40 p-4 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/10 resize-none text-slate-800 dark:text-slate-200 placeholder:text-slate-400"
                        />
                      )}

                      {/* Answer & Explanation (shown after submit) */}
                      {submittedMap[activeIdx] && (
                        <div className="space-y-4 pt-4 border-t border-slate-100 dark:border-slate-700">
                          {/* Correct Answer */}
                          <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-xl border border-emerald-100 dark:border-emerald-800">
                            <p className="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-2">
                              Correct Answer
                            </p>
                            <div className="text-emerald-800 dark:text-emerald-200 prose prose-sm dark:prose-invert max-w-none">
                              <ReactMarkdown
                                remarkPlugins={[remarkGfm, remarkMath]}
                                rehypePlugins={[rehypeKatex]}
                              >
                                {processLatexContent(
                                  String(
                                    currentQuestion.question.correct_answer,
                                  ),
                                )}
                              </ReactMarkdown>
                            </div>
                          </div>

                          {/* Explanation */}
                          {currentQuestion.question.explanation && (
                            <div>
                              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                                Explanation
                              </p>
                              <div className="text-slate-700 dark:text-slate-300 prose prose-sm dark:prose-invert max-w-none">
                                <ReactMarkdown
                                  remarkPlugins={[remarkGfm, remarkMath]}
                                  rehypePlugins={[rehypeKatex]}
                                >
                                  {processLatexContent(
                                    currentQuestion.question.explanation,
                                  )}
                                </ReactMarkdown>
                              </div>
                            </div>
                          )}

                          {/* Relevance Analysis (collapsible) */}
                          {currentQuestion.validation && (
                            <div className="border border-slate-200 dark:border-slate-600 rounded-xl overflow-hidden">
                              <button
                                onClick={() => setShowAnalysis(!showAnalysis)}
                                className="w-full px-4 py-3 flex items-center justify-between bg-slate-50 dark:bg-slate-700 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                              >
                                <div className="flex items-center gap-2 text-sm">
                                  <AlertCircle className="w-4 h-4 text-slate-400" />
                                  <span className="font-medium text-slate-600 dark:text-slate-300">
                                    Relevance Analysis
                                  </span>
                                  <span className="text-xs px-1.5 py-0.5 bg-slate-200 dark:bg-slate-600 text-slate-500 rounded">
                                    {currentQuestion.rounds || 1} round
                                    {(currentQuestion.rounds || 1) > 1
                                      ? "s"
                                      : ""}
                                  </span>
                                </div>
                                {showAnalysis ? (
                                  <ChevronUp className="w-4 h-4 text-slate-400" />
                                ) : (
                                  <ChevronDown className="w-4 h-4 text-slate-400" />
                                )}
                              </button>

                              {showAnalysis && (
                                <div className="px-4 py-3 space-y-3 text-sm bg-white dark:bg-slate-800">
                                  {currentQuestion.validation.kb_coverage && (
                                    <div>
                                      <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-600 uppercase tracking-wider mb-1">
                                        <Database className="w-3 h-3" />
                                        KB Coverage
                                      </div>
                                      <div className="text-slate-600 dark:text-slate-300 prose prose-xs dark:prose-invert max-w-none">
                                        <ReactMarkdown
                                          remarkPlugins={[
                                            remarkGfm,
                                            remarkMath,
                                          ]}
                                          rehypePlugins={[rehypeKatex]}
                                        >
                                          {processLatexContent(
                                            currentQuestion.validation
                                              .kb_coverage,
                                          )}
                                        </ReactMarkdown>
                                      </div>
                                    </div>
                                  )}
                                  {currentQuestion.validation
                                    .extension_points && (
                                    <div>
                                      <div className="flex items-center gap-1.5 text-xs font-bold text-amber-600 uppercase tracking-wider mb-1">
                                        <Zap className="w-3 h-3" />
                                        Extension Points
                                      </div>
                                      <div className="text-slate-600 dark:text-slate-300 prose prose-xs dark:prose-invert max-w-none">
                                        <ReactMarkdown
                                          remarkPlugins={[
                                            remarkGfm,
                                            remarkMath,
                                          ]}
                                          rehypePlugins={[rehypeKatex]}
                                        >
                                          {processLatexContent(
                                            currentQuestion.validation
                                              .extension_points,
                                          )}
                                        </ReactMarkdown>
                                      </div>
                                    </div>
                                  )}
                                  {currentQuestion.extended &&
                                    currentQuestion.validation
                                      .kb_connection && (
                                      <div>
                                        <div className="flex items-center gap-1.5 text-xs font-bold text-amber-600 uppercase tracking-wider mb-1">
                                          <Database className="w-3 h-3" />
                                          KB Connection
                                        </div>
                                        <div className="text-slate-600 dark:text-slate-300 prose prose-xs dark:prose-invert max-w-none">
                                          <ReactMarkdown
                                            remarkPlugins={[
                                              remarkGfm,
                                              remarkMath,
                                            ]}
                                            rehypePlugins={[rehypeKatex]}
                                          >
                                            {processLatexContent(
                                              currentQuestion.validation
                                                .kb_connection,
                                            )}
                                          </ReactMarkdown>
                                        </div>
                                      </div>
                                    )}
                                  {currentQuestion.extended &&
                                    currentQuestion.validation
                                      .extended_aspect && (
                                      <div>
                                        <div className="flex items-center gap-1.5 text-xs font-bold text-orange-600 uppercase tracking-wider mb-1">
                                          <Lightbulb className="w-3 h-3" />
                                          Extended Aspects
                                        </div>
                                        <div className="text-slate-600 dark:text-slate-300 prose prose-xs dark:prose-invert max-w-none">
                                          <ReactMarkdown
                                            remarkPlugins={[
                                              remarkGfm,
                                              remarkMath,
                                            ]}
                                            rehypePlugins={[rehypeKatex]}
                                          >
                                            {processLatexContent(
                                              currentQuestion.validation
                                                .extended_aspect,
                                            )}
                                          </ReactMarkdown>
                                        </div>
                                      </div>
                                    )}
                                  {currentQuestion.validation.reasoning && (
                                    <div>
                                      <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                                        Reasoning
                                      </div>
                                      <div className="text-slate-600 dark:text-slate-300 prose prose-xs dark:prose-invert max-w-none">
                                        <ReactMarkdown
                                          remarkPlugins={[
                                            remarkGfm,
                                            remarkMath,
                                          ]}
                                          rehypePlugins={[rehypeKatex]}
                                        >
                                          {processLatexContent(
                                            currentQuestion.validation
                                              .reasoning,
                                          )}
                                        </ReactMarkdown>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Footer Actions */}
                    <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800">
                      {!submittedMap[activeIdx] ? (
                        <button
                          onClick={handleSubmit}
                          disabled={!userAnswers[activeIdx]}
                          className="w-full py-3 bg-purple-600 text-white rounded-xl font-bold shadow-lg shadow-purple-500/20 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        >
                          Submit Answer
                        </button>
                      ) : (
                        <div className="flex items-center justify-center gap-2 py-3 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 rounded-xl">
                          <CheckCircle2 className="w-4 h-4" />
                          <span className="font-medium">Submitted</span>
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-slate-400">
                    <div className="text-center">
                      {isGenerating ? (
                        <>
                          <Loader2 className="w-12 h-12 animate-spin mx-auto mb-3 text-purple-500" />
                          <p className="text-lg font-medium text-slate-600 dark:text-slate-300">
                            Generating questions...
                          </p>
                          <p className="text-sm">
                            View progress in the Logs panel
                          </p>
                        </>
                      ) : (
                        <>
                          <Book className="w-12 h-12 mx-auto mb-3 opacity-30" />
                          <p className="text-sm">
                            Select a question to view details
                          </p>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Log Drawer */}
      <LogDrawer
        isOpen={showLogDrawer}
        onClose={() => setShowLogDrawer(false)}
        logs={questionState.logs || []}
        stage={stage}
        progress={progress.progress}
        subFocuses={subFocuses}
        mode={questionState.mode === "knowledge" ? "custom" : "mimic"}
        topic={questionState.topic}
        difficulty={questionState.difficulty}
        questionType={questionState.type}
        count={questionState.count}
        onClearLogs={() => setQuestionState((prev) => ({ ...prev, logs: [] }))}
      />

      {/* Add to Notebook Modal */}
      {currentQuestion && (
        <AddToNotebookModal
          isOpen={showNotebookModal}
          onClose={() => setShowNotebookModal(false)}
          recordType="question"
          title={`${questionState.topic} - ${currentQuestion.question.type || currentQuestion.question.question_type}`}
          userQuery={`Topic: ${questionState.topic}\nDifficulty: ${questionState.difficulty}\nType: ${questionState.type}`}
          output={`**Question:**\n${currentQuestion.question.question}\n\n**Options:**\n${
            currentQuestion.question.options
              ? Object.entries(currentQuestion.question.options)
                  .map(([k, v]) => `${k}. ${v}`)
                  .join("\n")
              : "N/A"
          }\n\n**Correct Answer:** ${currentQuestion.question.correct_answer}\n\n**Explanation:**\n${currentQuestion.question.explanation}`}
          metadata={{
            difficulty: questionState.difficulty,
            question_type: questionState.type,
            validation_rounds: currentQuestion.rounds,
            extended: currentQuestion.extended,
          }}
          kbName={questionState.selectedKb}
        />
      )}
    </div>
  );
}
