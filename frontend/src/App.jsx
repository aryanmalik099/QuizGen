import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { 
  Upload, FileText, CheckCircle, ExternalLink, Loader2, 
  Trash2, Plus, Sparkles, X, Image as ImageIcon, GripVertical, LogOut, User 
} from 'lucide-react';

// ⚠️ CRITICAL: This allows the Frontend to send/receive the "Login Cookie"
axios.defaults.withCredentials = true;

export default function App() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1);
  const [quizData, setQuizData] = useState([]);
  const [formUrl, setFormUrl] = useState("");
  const [title, setTitle] = useState("Untitled Quiz");
  
  // New State for User
  const [user, setUser] = useState(null);

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  // Drag and Drop Refs
  const dragItem = useRef();
  const dragOverItem = useRef();

  // --- 0. AUTH CHECK ON LOAD ---
  useEffect(() => {
    checkLoginStatus();
  }, []);

  const checkLoginStatus = async () => {
    try {
      const res = await axios.get(`${API_URL}/user`);
      if (res.data) {
        setUser(res.data);
      }
    } catch (err) {
      console.log("Not logged in");
    }
  };

  const handleLogin = () => {
    // Redirect the browser to the Backend's Login endpoint
    window.location.href =(`${API_URL}/login`);
  };

  const handleLogout = async () => {
    await axios.get(`${API_URL}/logout`);
    setUser(null);
  };

  // --- 1. FILE MANAGEMENT ---
  const handleFileChange = (e) => {
    const incoming = Array.from(e.target.files);
    const pdfs = [...files, ...incoming].filter(f => f.type === "application/pdf");
    const imgs = [...files, ...incoming].filter(f => f.type.startsWith("image/"));

    if (pdfs.length > 1) return alert("Only 1 PDF allowed.");
    if (imgs.length > 10) return alert("Maximum 10 images allowed.");
    setFiles([...pdfs, ...imgs]);
  };

  const removeFile = (name) => setFiles(files.filter(f => f.name !== name));

  // --- 2. AI GENERATION ---
  const handleGenerate = async () => {
    if (!files.length) return;
    setLoading(true);
    const formData = new FormData();
    files.forEach(f => formData.append("files", f));

    try {
      const res = await axios.post(`${API_URL}/generate-quiz`, formData);
      const clean = res.data.quiz_data.map(q => {
        const match = q.options.find(o => o.toLowerCase().trim() === q.correct_answer.toLowerCase().trim());
        return match ? { ...q, correct_answer: match } : { ...q, correct_answer: q.options[0] };
      });
      setQuizData(clean);
      setTitle(files[0].name.split('.')[0].replace(/_/g, ' '));
      setStep(2);
    } catch (err) {
      alert(err.response?.data?.detail || "AI Generation Failed");
    } finally {
      setLoading(false);
    }
  };

  // --- 3. REORDERING LOGIC ---
  const handleDragStart = (e, position) => { dragItem.current = position; };
  const handleDragEnter = (e, position) => { dragOverItem.current = position; };
  const handleDrop = () => {
    const copyListItems = [...quizData];
    const dragItemContent = copyListItems[dragItem.current];
    copyListItems.splice(dragItem.current, 1);
    copyListItems.splice(dragOverItem.current, 0, dragItemContent);
    dragItem.current = null;
    dragOverItem.current = null;
    setQuizData(copyListItems);
  };

  // --- 4. EDITOR ACTIONS ---
  const handlePublish = async (e) => {
    if (e) e.preventDefault();
    
    if (!user) {
        if(!confirm("You are not logged in. The quiz will be created by the Robot. Continue?")) return;
    }

    setLoading(true);
    try {
      const payload = { title: title || "Untitled Quiz", questions: quizData };
      const res = await axios.post(`${API_URL}/publish-quiz`, payload);
      setFormUrl(res.data.form_url);
      setStep(3);
    } catch (err) {
      alert(`Network Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const updateQ = (i, field, val) => {
    const copy = [...quizData];
    copy[i][field] = val;
    setQuizData(copy);
  };

  const updateOpt = (qI, oI, val) => {
    const copy = [...quizData];
    if (copy[qI].correct_answer === copy[qI].options[oI]) copy[qI].correct_answer = val;
    copy[qI].options[oI] = val;
    setQuizData(copy);
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900 pb-20">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 border-b bg-white/80 backdrop-blur-md px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-indigo-600 cursor-pointer" onClick={() => window.location.reload()}>
            <Sparkles className="h-6 w-6" /> <span className="text-xl tracking-tight text-slate-900">QuizGen AI</span>
          </div>
          
          <div className="flex items-center gap-6">
            <div className="hidden md:flex gap-4 text-xs font-bold uppercase tracking-widest text-slate-400">
                {['Upload', 'Edit', 'Done'].map((s, i) => (
                <span key={s} className={step === i + 1 ? "text-indigo-600" : ""}>{i + 1}. {s}</span>
                ))}
            </div>

            {/* AUTH BUTTONS */}
            {user ? (
                <div className="flex items-center gap-3 pl-6 border-l border-slate-200">
                    <div className="text-right hidden sm:block">
                        <p className="text-xs font-bold text-slate-900">{user.name}</p>
                        <p className="text-[10px] text-slate-400">{user.email}</p>
                    </div>
                    {user.picture ? (
                        <img src={user.picture} alt="Profile" className="h-8 w-8 rounded-full border border-slate-200" />
                    ) : (
                        <div className="h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold">
                            {user.name?.[0]}
                        </div>
                    )}
                    <button onClick={handleLogout} className="p-2 text-slate-400 hover:text-red-500 transition" title="Logout">
                        <LogOut className="h-4 w-4" />
                    </button>
                </div>
            ) : (
                <button 
                    onClick={handleLogin}
                    className="flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800 transition shadow-lg shadow-slate-200"
                >
                    <User className="h-4 w-4" /> Sign In
                </button>
            )}
          </div>
        </div>
      </nav>

      <main className="mx-auto mt-12 max-w-3xl px-6">
        {/* STEP 1: UPLOAD */}
        {step === 1 && (
          <div className="animate-in fade-in slide-in-from-bottom-4">
            <div className="mb-10 text-center">
              <h1 className="text-4xl font-black tracking-tight">Generate Quizzes Instantly</h1>
              <p className="mt-2 text-slate-500">Combine your lecture notes and PDF syllabus.</p>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-2xl shadow-indigo-100/30 transition-all">
              <label className="group relative block cursor-pointer rounded-2xl border-2 border-dashed border-slate-200 p-12 transition hover:border-indigo-400 hover:bg-indigo-50/50 text-center">
                <input type="file" multiple accept=".pdf,image/*" onChange={handleFileChange} className="hidden" />
                <Upload className="mx-auto h-12 w-12 text-indigo-500 transition group-hover:scale-110 mb-4" />
                <span className="inline-block rounded-full bg-indigo-600 px-8 py-3 text-sm font-bold text-white shadow-lg">Browse Files</span>
                <p className="mt-4 text-[10px] font-bold uppercase tracking-widest text-slate-400">1 PDF + 10 Images Max</p>
              </label>

              {files.length > 0 && (
                <div className="mt-8 space-y-2">
                  {files.map((f) => (
                    <div key={f.name} className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 p-3">
                      <div className="flex items-center gap-3 truncate">
                        {f.type === "application/pdf" ? <FileText className="h-4 w-4 text-red-500" /> : <ImageIcon className="h-4 w-4 text-blue-500" />}
                        <span className="truncate text-sm font-medium">{f.name}</span>
                      </div>
                      <button onClick={() => removeFile(f.name)} className="rounded-md p-1 hover:bg-red-100 text-slate-400 hover:text-red-600 transition"><X className="h-4 w-4" /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button 
              onClick={handleGenerate} 
              disabled={loading || !files.length}
              className="mt-8 flex w-full items-center justify-center gap-3 rounded-2xl bg-slate-900 py-4 text-lg font-bold text-white transition hover:bg-slate-800 disabled:bg-slate-200 shadow-xl"
            >
              {loading ? <><Loader2 className="animate-spin" /> Studying Files...</> : <><Sparkles className="h-5 w-5" /> Generate My Quiz</>}
            </button>
          </div>
        )}

        {/* STEP 2: EDITOR */}
        {step === 2 && (
          <div className="space-y-6 animate-in fade-in zoom-in-95">
            <div className="sticky top-24 z-40 flex items-center justify-between rounded-2xl border bg-white/95 p-4 shadow-xl backdrop-blur-md">
              <input value={title} onChange={(e) => setTitle(e.target.value)} className="flex-1 bg-transparent text-xl font-black focus:ring-0 truncate mr-4" />
              <div className="flex gap-2">
                 <button onClick={() => setQuizData([])} className="p-2 text-slate-400 hover:text-red-500 transition" title="Clear All"><Trash2 className="h-5 w-5" /></button>
                 <button onClick={handlePublish} disabled={loading} className="rounded-xl bg-indigo-600 px-6 py-2.5 font-bold text-white shadow-lg shadow-indigo-200 hover:bg-indigo-700 active:scale-95 transition">
                  {loading ? <Loader2 className="animate-spin" /> : 'Publish Quiz'}
                </button>
              </div>
            </div>

            <div className="space-y-4">
              {quizData.map((q, qI) => (
                <div 
                  key={qI} 
                  draggable
                  onDragStart={(e) => handleDragStart(e, qI)}
                  onDragEnter={(e) => handleDragEnter(e, qI)}
                  onDragEnd={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  className="group relative rounded-3xl border border-slate-100 bg-white p-6 shadow-sm transition-all hover:shadow-md cursor-grab active:cursor-grabbing hover:border-indigo-200"
                >
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-300 group-hover:text-indigo-400 transition">
                    <GripVertical className="h-6 w-6" />
                  </div>

                  <div className="pl-8">
                    <div className="mb-4 flex items-center justify-between">
                      <span className="rounded-full bg-indigo-50 px-3 py-1 text-[10px] font-bold text-indigo-600 uppercase tracking-widest">
                        Question {qI + 1}
                      </span>
                      <button 
                        onClick={() => setQuizData(quizData.filter((_, i) => i !== qI))} 
                        className="text-slate-300 hover:text-red-500 p-1 transition"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>

                    <textarea 
                      value={q.question} 
                      onChange={(e) => updateQ(qI, 'question', e.target.value)} 
                      className="w-full border-none p-0 text-lg font-bold focus:ring-0 bg-transparent resize-none placeholder-slate-300" 
                      rows={2} 
                      placeholder="Type your question..."
                    />
                    
                    <div className="mt-6 space-y-2">
                      {q.options.map((opt, oI) => (
                        <div 
                          key={oI} 
                          onClick={() => updateQ(qI, 'correct_answer', opt)} 
                          className={`flex items-center rounded-2xl border-2 p-3 transition-all ${
                            q.correct_answer === opt ? 'border-indigo-500 bg-indigo-50/50' : 'border-slate-50 bg-slate-50 hover:border-slate-200'
                          }`}
                        >
                          <div className={`mr-4 h-4 w-4 rounded-full border-2 transition ${
                            q.correct_answer === opt ? 'border-indigo-600 bg-indigo-600' : 'border-slate-300 bg-white'
                          }`} />
                          <input 
                            value={opt} 
                            onChange={(e) => updateOpt(qI, oI, e.target.value)} 
                            onClick={(e) => e.stopPropagation()} 
                            className="flex-1 bg-transparent text-sm font-semibold focus:ring-0" 
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button onClick={() => setQuizData([...quizData, { question: "New Question", options: ["A", "B"], correct_answer: "A" }])} className="w-full rounded-2xl border-2 border-dashed border-slate-200 py-5 font-bold text-slate-400 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600 transition flex items-center justify-center gap-2">
              <Plus className="h-5 w-5" /> Add New Question
            </button>
          </div>
        )}

        {/* STEP 3: SUCCESS */}
        {step === 3 && (
          <div className="py-20 text-center animate-in zoom-in-95">
            <div className="mx-auto mb-8 flex h-24 w-24 items-center justify-center rounded-full bg-green-100 text-green-600 shadow-xl shadow-green-100 animate-bounce">
              <CheckCircle className="h-12 w-12" />
            </div>
            <h2 className="text-4xl font-black">Ready to Launch!</h2>
            <p className="mt-4 text-slate-500 max-w-sm mx-auto">Your draft is live in Google Forms. You can now tweak the theme and send it to your students.</p>
            <a href={formUrl} target="_blank" rel="noopener noreferrer" className="mt-10 inline-flex items-center rounded-2xl bg-indigo-600 px-10 py-5 text-xl font-bold text-white shadow-2xl hover:bg-indigo-700 hover:-translate-y-1 transition active:scale-95">
              Open Forms Editor <ExternalLink className="ml-3 h-6 w-6" />
            </a>
            <button onClick={() => setStep(1)} className="mt-12 block w-full font-bold text-slate-400 hover:text-indigo-600">Create New Quiz</button>
          </div>
        )}
      </main>
    </div>
  );
}