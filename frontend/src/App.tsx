import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { AlertTriangle, CheckCircle2, Shield, Loader2, PlayCircle, Video } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = 'http://localhost:8000/api/v1';

function App() {
  const [isCapturing, setIsCapturing] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [streamActive, setStreamActive] = useState(false);
  const [timeLeft, setTimeLeft] = useState(10);

  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setStreamActive(true);
        setError(null);
      } catch (err) {
        console.error("Camera access denied or failed", err);
        setError("Please allow camera access in your browser to use live detection.");
      }
    };

    startCamera();

    return () => {
      // Cleanup stream on unmount
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const playAlertSound = () => {
    try {
      const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioContext();

      const playBeep = (timeOffset: number) => {
        const osc = ctx.createOscillator();
        const gainNode = ctx.createGain();

        osc.type = 'square';
        osc.frequency.setValueAtTime(880, ctx.currentTime + timeOffset);
        osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + timeOffset + 0.15);

        gainNode.gain.setValueAtTime(0.1, ctx.currentTime + timeOffset);
        gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + timeOffset + 0.15);

        osc.connect(gainNode);
        gainNode.connect(ctx.destination);

        osc.start(ctx.currentTime + timeOffset);
        osc.stop(ctx.currentTime + timeOffset + 0.15);
      };

      playBeep(0);
      playBeep(0.2);
      playBeep(0.4);
    } catch (e) {
      console.log("Audio not supported");
    }
  };

  const startCapture = () => {
    if (!videoRef.current || !videoRef.current.srcObject) return;

    setResults(null);
    setIsCapturing(true);
    setTimeLeft(10);
    chunksRef.current = [];

    const stream = videoRef.current.srcObject as MediaStream;
    const mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
    mediaRecorderRef.current = mediaRecorder;

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        chunksRef.current.push(e.data);
      }
    };

    mediaRecorder.onstop = async () => {
      setIsCapturing(false);
      setIsAnalyzing(true);

      const blob = new Blob(chunksRef.current, { type: 'video/webm' });
      const formData = new FormData();
      formData.append('file', blob, 'webcam-capture.webm');

      try {
        // Upload directly to the standard /analyze endpoint!
        const response = await axios.post(`${API_URL}/video/analyze?sample_fps=2`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });

        setResults(response.data);
        if (response.data.alerts_count > 0) {
          playAlertSound();
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || "Analysis failed.");
      } finally {
        setIsAnalyzing(false);
      }
    };

    mediaRecorder.start();

    // Stop recording after 10 seconds
    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-[#0f172a] text-slate-200 p-8 font-sans selection:bg-indigo-500/30">
      <div className="max-w-5xl mx-auto space-y-8">

        {/* Header */}
        <header className="flex items-center justify-between pb-6 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
              <Shield className="w-8 h-8 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">VideoAI Intelligence</h1>
              <p className="text-sm text-slate-400">Live Browser Capture Demo</p>
            </div>
          </div>
        </header>

        {/* Main Action Area */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          <div className="lg:col-span-1 space-y-6">
            <div className="bg-[#1e293b] rounded-2xl p-6 border border-slate-800 shadow-xl relative overflow-hidden">
              <h2 className="text-xl font-semibold text-white mb-2">Live Detection Test</h2>
              <p className="text-slate-400 text-sm mb-6">
                Your browser is showing the live webcam feed. Click start to record a 10-second clip.
              </p>

              {/* Live Video Preview Player */}
              <div className="relative rounded-xl overflow-hidden bg-slate-900 border border-slate-700 mb-6 aspect-video">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover transform scale-x-[-1]"
                />
                {!streamActive && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500">
                    <Video className="w-8 h-8 mb-2 opacity-50" />
                    <span className="text-xs">Waiting for camera...</span>
                  </div>
                )}
                {isCapturing && (
                  <div className="absolute top-3 left-3 bg-red-500/90 text-white text-[10px] font-bold uppercase px-2 py-1 rounded-md flex items-center shadow-lg">
                    <div className="w-2 h-2 rounded-full bg-white animate-pulse mr-1.5" />
                    REC {timeLeft}s
                  </div>
                )}
              </div>

              <button
                onClick={startCapture}
                disabled={isCapturing || isAnalyzing || !streamActive}
                className="w-full flex items-center justify-center space-x-2 bg-indigo-500 hover:bg-indigo-600 disabled:bg-slate-700 disabled:text-slate-400 text-white py-3 px-4 rounded-xl font-medium transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                {isCapturing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Recording... ({timeLeft}s)</span>
                  </>
                ) : isAnalyzing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <PlayCircle className="w-5 h-5" />
                    <span>Start 10s Capture</span>
                  </>
                )}
              </button>

              {error && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start space-x-2 text-red-400 text-sm">
                  <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
            </div>
          </div>

          {/* Results Area */}
          <div className="lg:col-span-2 space-y-6">
            <AnimatePresence mode="popLayout">
              {isAnalyzing && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex flex-col items-center justify-center h-64 bg-[#1e293b] rounded-2xl border border-slate-800 border-dashed"
                >
                  <div className="relative">
                    <div className="absolute -inset-4 bg-indigo-500/20 rounded-full blur-xl animate-pulse"></div>
                    <Shield className="w-12 h-12 text-indigo-400 animate-pulse relative z-10" />
                  </div>
                  <p className="mt-6 text-slate-300 font-medium">Running detection inference...</p>
                  <p className="text-sm text-slate-500 mt-2">Uploading and analyzing frames.</p>
                </motion.div>
              )}

              {results && !isAnalyzing && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-6"
                >
                  {/* Summary Stats */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <StatCard title="Frames Analyzed" value={results.analysis.frames_analyzed} />
                    <StatCard title="Duration" value={`${results.analysis.duration_seconds}s`} />
                    <StatCard title="Classes Found" value={results.analysis.unique_classes_detected.length} />
                    <StatCard
                      title="Alerts Generated"
                      value={results.alerts_count}
                      alert={results.alerts_count > 0}
                    />
                  </div>

                  {/* Alerts Section */}
                  {results.alerts_count > 0 ? (
                    <div className="space-y-3">
                      <h3 className="text-lg font-semibold flex items-center space-x-2">
                        <AlertTriangle className="w-5 h-5 text-amber-500" />
                        <span>Security Alerts Triggered</span>
                      </h3>
                      <div className="grid gap-3">
                        {results.alerts_generated.map((alert: any, i: number) => (
                          <div key={i} className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl flex items-start justify-between">
                            <div>
                              <div className="flex items-center space-x-2 mb-1">
                                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${alert.severity === 'critical' ? 'bg-red-500/20 text-red-400' :
                                  alert.severity === 'high' ? 'bg-orange-500/20 text-orange-400' :
                                    'bg-amber-500/20 text-amber-400'
                                  }`}>
                                  {alert.severity}
                                </span>
                                <h4 className="font-semibold text-white">{alert.title}</h4>
                              </div>
                              <p className="text-sm text-slate-400">{alert.description}</p>
                            </div>
                            <div className="text-right">
                              <div className="text-xs text-slate-500">Confidence</div>
                              <div className="font-medium text-amber-400">{(alert.confidence * 100).toFixed(0)}%</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-emerald-500/10 border border-emerald-500/20 p-6 rounded-xl flex items-center justify-center space-x-3 text-emerald-400">
                      <CheckCircle2 className="w-6 h-6" />
                      <span className="font-medium">No threats detected in this capture. Area is secure.</span>
                    </div>
                  )}

                  {/* Raw Detections List */}
                  <div className="space-y-3">
                    <h3 className="text-lg font-semibold text-slate-300">Raw Detections</h3>
                    <div className="bg-[#1e293b] rounded-xl border border-slate-800 divide-y divide-slate-800/50 max-h-80 overflow-y-auto">
                      {results.detections.length > 0 ? (
                        results.detections.map((frame: any, i: number) => (
                          <div key={i} className="p-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors">
                            <div className="flex items-center space-x-4">
                              <div className="w-12 h-12 rounded-lg bg-slate-900 border border-slate-800 flex flex-col items-center justify-center shrink-0">
                                <span className="text-xs text-slate-500">Sec</span>
                                <span className="text-sm font-mono text-indigo-400">{frame.timestamp_seconds.toFixed(1)}</span>
                              </div>
                              <div>
                                <div className="font-medium text-slate-200">
                                  {frame.objects.map((o: any) => o.class).join(', ')}
                                </div>
                                <div className="text-xs text-slate-500 mt-1">
                                  Frame {frame.frame_number} • {frame.objects_detected} object(s)
                                </div>
                              </div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="p-8 text-center text-slate-500">
                          No objects detected in any frame.
                        </div>
                      )}
                    </div>
                  </div>

                </motion.div>
              )}
            </AnimatePresence>
          </div>

        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, alert = false }: { title: string, value: string | number, alert?: boolean }) {
  return (
    <div className={`p-4 rounded-xl border ${alert ? 'bg-red-500/10 border-red-500/20' : 'bg-[#1e293b] border-slate-800'}`}>
      <div className="text-xs text-slate-400 mb-1">{title}</div>
      <div className={`text-2xl font-semibold tracking-tight ${alert ? 'text-red-400' : 'text-white'}`}>
        {value}
      </div>
    </div>
  );
}

export default App;
