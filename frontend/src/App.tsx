import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { AlertTriangle, CheckCircle2, Shield, Loader2, PlayCircle, Video, Bell, BellOff, Clock, X, Image as ImageIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = 'http://localhost:8000/api/v1';

function App() {
  const [isCapturing, setIsCapturing] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [streamActive, setStreamActive] = useState(false);
  const [timeLeft, setTimeLeft] = useState(10);
  const [alertHistory, setAlertHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<any>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  // Start webcam on load
  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        if (videoRef.current) videoRef.current.srcObject = stream;
        setStreamActive(true);
        setError(null);
      } catch {
        setError("Please allow camera access in your browser to use live detection.");
      }
    };
    startCamera();
    return () => {
      if (videoRef.current?.srcObject) {
        (videoRef.current.srcObject as MediaStream).getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  // Fetch alert history on load
  useEffect(() => {
    fetchAlertHistory();
  }, []);

  const fetchAlertHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await axios.get(`${API_URL}/video/alerts?limit=50`);
      setAlertHistory(res.data.alerts);
    } catch {
      // silently fail if DB not available
    } finally {
      setLoadingHistory(false);
    }
  };

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
      playBeep(0); playBeep(0.2); playBeep(0.4);
    } catch { /* no-op */ }
  };

  const startCapture = () => {
    if (!videoRef.current?.srcObject) return;
    setResults(null);
    setIsCapturing(true);
    setTimeLeft(10);
    chunksRef.current = [];

    const stream = videoRef.current.srcObject as MediaStream;
    const mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
    mediaRecorderRef.current = mediaRecorder;

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      setIsCapturing(false);
      setIsAnalyzing(true);
      const blob = new Blob(chunksRef.current, { type: 'video/webm' });
      const formData = new FormData();
      formData.append('file', blob, 'webcam-capture.webm');
      try {
        const response = await axios.post(`${API_URL}/video/analyze?sample_fps=2`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        setResults(response.data);
        if (response.data.alerts_count > 0) {
          playAlertSound();
          fetchAlertHistory(); // Refresh history after new alerts
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || "Analysis failed.");
      } finally {
        setIsAnalyzing(false);
      }
    };

    mediaRecorder.start();
    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          if (mediaRecorderRef.current?.state !== 'inactive') mediaRecorderRef.current?.stop();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const severityColor = (severity: string) => {
    if (severity === 'critical') return 'bg-red-500/20 text-red-400 border-red-500/30';
    if (severity === 'high') return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
  };

  const timeAgo = (isoString: string) => {
    const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  };

  return (
    <div className="min-h-screen text-slate-200 p-6 font-sans selection:bg-indigo-500/30">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <header className="flex items-center justify-between pb-5 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
              <Shield className="w-8 h-8 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">VideoAI Intelligence</h1>
              <p className="text-sm text-slate-400">AI-Powered Security Surveillance</p>
            </div>
          </div>
          {/* <div className="flex items-center space-x-2 text-xs text-slate-500 bg-slate-800/50 px-3 py-1.5 rounded-full border border-slate-700">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>System Online</span>
          </div> */}
        </header>

        {/* Top Row: Webcam + Live Results (50/50) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Webcam Panel */}
          <div className="bg-[#1e293b] rounded-2xl p-6 border border-slate-800 shadow-xl">
            <h2 className="text-lg font-semibold text-white mb-1">Live Detection Feed</h2>
            <p className="text-slate-400 text-sm mb-4">Click start to record and analyze a 10-second clip.</p>

            <div className="relative rounded-xl overflow-hidden bg-slate-900 border border-slate-700 mb-4 aspect-video">
              <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover transform scale-x-[-1]" />
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
                <><Loader2 className="w-5 h-5 animate-spin" /><span>Recording... ({timeLeft}s)</span></>
              ) : isAnalyzing ? (
                <><Loader2 className="w-5 h-5 animate-spin" /><span>Analyzing with AI...</span></>
              ) : (
                <><PlayCircle className="w-5 h-5" /><span>Start 10s Capture</span></>
              )}
            </button>

            {error && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start space-x-2 text-red-400 text-sm">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </div>

          {/* Live Analysis Results */}
          <div className="space-y-4">
            <AnimatePresence mode="popLayout">
              {isAnalyzing && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  className="flex flex-col items-center justify-center h-64 bg-[#1e293b] rounded-2xl border border-slate-800 border-dashed"
                >
                  <div className="relative">
                    <div className="absolute -inset-4 bg-indigo-500/20 rounded-full blur-xl animate-pulse" />
                    <Shield className="w-12 h-12 text-indigo-400 animate-pulse relative z-10" />
                  </div>
                  <p className="mt-6 text-slate-300 font-medium">Running AI Detection...</p>
                  <p className="text-sm text-slate-500 mt-2">Analyzing frames</p>
                </motion.div>
              )}

              {results && !isAnalyzing && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-3">
                    <StatCard title="Frames Analyzed" value={results.analysis.frames_analyzed} />
                    <StatCard title="Duration" value={`${results.analysis.duration_seconds}s`} />
                    <StatCard title="Classes Found" value={results.analysis.unique_classes_detected.length} />
                    <StatCard title="Alerts" value={results.alerts_count} alert={results.alerts_count > 0} />
                    {results.reid_summary && (
                      <>
                        <StatCard title="Unique Persons" value={results.reid_summary.total_unique_persons} />
                        <StatCard
                          title="Repeat/Frequent"
                          value={`${results.reid_summary.repeat_persons}/${results.reid_summary.frequent_persons}`}
                          alert={results.reid_summary.frequent_persons > 0}
                        />
                      </>
                    )}
                  </div>

                  {/* Alerts */}
                  {results.alerts_generated.filter((a: any) => a.alert_type !== 'frequent_person' && a.alert_type !== 'repeat_person').length > 0 ? (
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold flex items-center space-x-2 text-amber-400">
                        <AlertTriangle className="w-4 h-4" /><span>Security Alerts Triggered</span>
                      </h3>
                      {results.alerts_generated.filter((a: any) => a.alert_type !== 'frequent_person' && a.alert_type !== 'repeat_person').map((alert: any, i: number) => (
                        <div key={i} className={`p-4 rounded-xl border flex items-start justify-between ${severityColor(alert.severity)}`}>
                          <div>
                            <div className="flex items-center space-x-2 mb-1">
                              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-black/20">{alert.severity}</span>
                              <h4 className="font-semibold text-white text-sm">{alert.title}</h4>
                            </div>
                            <p className="text-xs text-slate-400">{alert.description}</p>
                            <div className="flex items-center space-x-3 mt-2">
                              {alert.notified ? (
                                <span className="flex items-center space-x-1 text-[10px] text-emerald-400">
                                  <Bell className="w-3 h-3" /><span>SMS Sent</span>
                                </span>
                              ) : (
                                <span className="flex items-center space-x-1 text-[10px] text-slate-500">
                                  <BellOff className="w-3 h-3" /><span>SMS not sent</span>
                                </span>
                              )}
                            </div>
                          </div>
                          {alert.confidence && (
                            <div className="text-right shrink-0 ml-3">
                              <div className="text-xs text-slate-500">Confidence</div>
                              <div className="font-medium text-sm">{(alert.confidence * 100).toFixed(0)}%</div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-xl flex items-center space-x-3 text-emerald-400">
                      <CheckCircle2 className="w-5 h-5" />
                      <span className="text-sm font-medium">No threats detected. Area is secure.</span>
                    </div>
                  )}

                  {/* Raw Detections
                  <div className="bg-[#1e293b] rounded-xl border border-slate-800 max-h-48 overflow-y-auto">
                    <div className="p-3 border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase tracking-wider">Raw Detections</div>
                    {results.detections.length > 0 ? results.detections.map((frame: any, i: number) => (
                      <div key={i} className="p-3 flex items-center justify-between hover:bg-slate-800/30 transition-colors border-b border-slate-800/50 last:border-0">
                        <div className="flex items-center space-x-3">
                          <span className="text-xs font-mono text-indigo-400 w-12">{frame.timestamp_seconds.toFixed(1)}s</span>
                          <span className="text-sm text-slate-300">
                            {frame.objects.map((o: any, oi: number) => (
                              <span key={oi}>
                                {o.class === 'person' && o.person_id ? (
                                  <span
                                    className={`inline-flex items-center space-x-1 mr-1 px-1.5 py-0.5 rounded text-[10px] font-bold border ${
                                      o.tag_color === 'red'
                                        ? 'bg-red-500/20 border-red-500/40 text-red-300'
                                        : o.tag_color === 'yellow'
                                        ? 'bg-yellow-500/20 border-yellow-500/40 text-yellow-300'
                                        : 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                                    }`}
                                  >
                                    <span>{o.person_id}</span>
                                    {o.sighting_count > 1 && <span>×{o.sighting_count}</span>}
                                  </span>
                                ) : (
                                  <span className="mr-1">{o.class}</span>
                                )}
                              </span>
                            ))}
                          </span>
                        </div>
                        <span className="text-xs text-slate-500">{frame.objects_detected} obj</span>
                      </div>
                    )) : (
                      <div className="p-6 text-center text-slate-500 text-sm">No objects detected.</div>
                    )}
                  </div> */}


                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Bottom Row: Alert History (Full Width) */}
        <div className="bg-[#1e293b] rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Clock className="w-5 h-5 text-indigo-400" />
              <h2 className="text-lg font-semibold text-white">Alert History & Logs</h2>
              <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">{alertHistory.length} records</span>
            </div>
            <button
              onClick={fetchAlertHistory}
              className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors px-3 py-1.5 rounded-lg border border-indigo-500/20 hover:border-indigo-500/40"
            >
              {loadingHistory ? 'Refreshing...' : '↻ Refresh'}
            </button>
          </div>

          {loadingHistory ? (
            <div className="p-12 text-center text-slate-500 text-sm">Loading history from database...</div>
          ) : alertHistory.length === 0 ? (
            <div className="p-12 text-center">
              <Shield className="w-10 h-10 text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500 text-sm">No alerts recorded yet.</p>
              <p className="text-slate-600 text-xs mt-1">Alerts will appear here after the first detection.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wider text-slate-500 border-b border-slate-800">
                    <th className="text-left p-4">Snapshot</th>
                    <th className="text-left p-4">Time</th>
                    <th className="text-left p-4">Severity</th>
                    <th className="text-left p-4">Alert</th>
                    <th className="text-left p-4">Description</th>
                    <th className="text-left p-4">Confidence</th>
                    <th className="text-left p-4">SMS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {alertHistory.map((alert: any) => (
                    <tr key={alert.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="p-4">
                        {alert.screenshot_urls && alert.screenshot_urls.length > 0 ? (
                          <div
                            className="relative w-16 h-12 rounded overflow-hidden border border-slate-700 bg-slate-800 cursor-pointer group"
                            onClick={() => setSelectedAlert(alert)}
                          >
                            <img src={alert.screenshot_urls[0]} alt="Incident snapshot" className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300" />
                            {alert.screenshot_urls.length > 1 && (
                              <div className="absolute bottom-0 right-0 bg-black/70 text-white text-[8px] px-1 font-bold">
                                1/{alert.screenshot_urls.length}
                              </div>
                            )}
                            <div className="absolute inset-0 bg-indigo-500/0 group-hover:bg-indigo-500/20 transition-colors flex items-center justify-center">
                              <ImageIcon className="w-4 h-4 text-white opacity-0 group-hover:opacity-100 drop-shadow-md transition-opacity" />
                            </div>
                          </div>
                        ) : (
                          <div className="w-16 h-12 rounded border border-slate-800 border-dashed bg-slate-900/50 flex items-center justify-center">
                            <span className="text-[9px] text-slate-600">No Image</span>
                          </div>
                        )}
                      </td>
                      <td className="p-4 text-slate-400 whitespace-nowrap">{timeAgo(alert.timestamp)}</td>
                      <td className="p-4">
                        <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${severityColor(alert.severity)}`}>
                          {alert.severity}
                        </span>
                      </td>
                      <td className="p-4 font-medium text-white whitespace-nowrap">{alert.title}</td>
                      <td className="p-4 text-slate-400 max-w-xs truncate">{alert.description}</td>
                      <td className="p-4 text-slate-300">
                        {alert.confidence ? `${(alert.confidence * 100).toFixed(0)}%` : '—'}
                      </td>
                      <td className="p-4">
                        {alert.notified
                          ? <span className="flex items-center space-x-1 text-emerald-400"><Bell className="w-3.5 h-3.5" /><span>Sent</span></span>
                          : <span className="flex items-center space-x-1 text-slate-500"><BellOff className="w-3.5 h-3.5" /><span>—</span></span>
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>

      {/* Full Screen Image Modal */}
      <AnimatePresence>
        {selectedAlert && selectedAlert.screenshot_urls && selectedAlert.screenshot_urls.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-sm"
            onClick={() => setSelectedAlert(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="bg-[#1e293b] rounded-2xl border border-slate-700 shadow-2xl max-w-5xl w-full overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900/50">
                <div>
                  <h3 className="text-lg font-semibold text-white">{selectedAlert.title}</h3>
                  <p className="text-xs text-slate-400">{selectedAlert.description}</p>
                </div>
                <button
                  onClick={() => setSelectedAlert(null)}
                  className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Horizontal Scroll Gallery */}
              <div className="p-6 bg-[#0f172a]">
                <div className="flex space-x-4 overflow-x-auto pb-4 snap-x snap-mandatory hide-scrollbar">
                  {selectedAlert.screenshot_urls.map((url: string, idx: number) => (
                    <div key={idx} className="shrink-0 w-[80%] md:w-[60%] lg:w-[45%] snap-center rounded-xl overflow-hidden border border-slate-700 bg-black relative">
                      <img src={url} alt={`Frame ${idx + 1}`} className="w-full h-auto object-contain max-h-[60vh]" />
                      <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-md text-white text-xs px-2 py-1 rounded-md border border-white/10 font-mono">
                        Frame {idx + 1} of {selectedAlert.screenshot_urls.length}
                      </div>
                    </div>
                  ))}
                </div>
                {selectedAlert.screenshot_urls.length > 1 && (
                  <p className="text-center text-xs text-slate-500 mt-2">
                    ↔ Swipe or scroll horizontally to view context frames
                  </p>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}

function StatCard({ title, value, alert = false }: { title: string; value: string | number; alert?: boolean }) {
  return (
    <div className={`p-4 rounded-xl border ${alert ? 'bg-red-500/10 border-red-500/20' : 'bg-[#0f172a] border-slate-800'}`}>
      <div className="text-xs text-slate-400 mb-1">{title}</div>
      <div className={`text-2xl font-semibold tracking-tight ${alert ? 'text-red-400' : 'text-white'}`}>{value}</div>
    </div>
  );
}

export default App;
