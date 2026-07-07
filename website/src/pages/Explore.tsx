import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import LiteratureGraphViewer from "../components/LiteratureGraphViewer";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

const Explore = () => {
  const [searchParams] = useSearchParams();
  const [graphData, setGraphData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const backend = searchParams.get("backend") || window.location.origin;
  const cypherQuery = searchParams.get("cypher_query") || "";

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const url = new URL("/api/graph", backend);
        if (cypherQuery) url.searchParams.set("cypher_query", cypherQuery);
        const response = await fetch(url.toString());
        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || `Server error (${response.status})`);
        }
        setGraphData(await response.json());
      } catch (err: any) {
        console.error("Graph fetch failed:", err);
        setError(err.message || "Failed to load graph");
        toast.error("Failed to load literature graph: " + (err.message || "unknown error"));
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [backend, cypherQuery]);

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-black text-white">
        <Loader2 className="w-12 h-12 animate-spin mb-4" />
        <p className="text-[10px] font-mono uppercase tracking-widest text-gray-500">
          Loading literature graph...
        </p>
      </div>
    );
  }

  if (error || !graphData) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-black text-white px-6 text-center">
        <h1 className="text-sm font-black uppercase tracking-widest mb-3">Graph Load Error</h1>
        <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest max-w-md mb-6">
          {error || "No graph data"}
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="bg-white text-black px-5 py-2 rounded-full text-[10px] font-black uppercase tracking-widest"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-background">
      <LiteratureGraphViewer data={graphData} onClose={() => setGraphData(null)} />
    </main>
  );
};

export default Explore;
