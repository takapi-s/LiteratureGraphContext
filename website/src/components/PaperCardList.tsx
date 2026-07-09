import { BookOpen } from 'lucide-react';

export type PaperSummary = {
  paper_id: string;
  title: string;
  year?: number | null;
  authors?: string;
  methods?: string[];
  tasks?: string[];
  claim_count?: number;
  limitation_count?: number;
  contribution_count?: number;
};

type PaperCardListProps = {
  papers: PaperSummary[];
  selectedFile: string | null;
  onPaperClick: (paperId: string) => void;
  searchQuery: string;
  isDark: boolean;
};

function matchesSearch(paper: PaperSummary, query: string): boolean {
  const q = query.toLowerCase();
  const haystack = [
    paper.paper_id,
    paper.title,
    paper.authors || '',
    ...(paper.methods || []),
    ...(paper.tasks || []),
  ].join(' ').toLowerCase();
  return haystack.includes(q);
}

export function PaperCardList({
  papers,
  selectedFile,
  onPaperClick,
  searchQuery,
  isDark,
}: PaperCardListProps) {
  const filtered = papers.filter(p => !searchQuery || matchesSearch(p, searchQuery));

  if (filtered.length === 0) {
    return (
      <p className={`px-3 py-4 text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
        No papers match your filter.
      </p>
    );
  }

  return (
    <div className="space-y-2 px-1 py-1">
      {filtered.map(paper => {
        const path = `papers/${paper.paper_id}`;
        const isSelected = selectedFile === path;
        const methods = (paper.methods || []).slice(0, 2);
        const tasks = (paper.tasks || []).slice(0, 2);
        const tags = [...tasks, ...methods].slice(0, 3);

        return (
          <button
            key={paper.paper_id}
            type="button"
            onClick={() => onPaperClick(paper.paper_id)}
            className={`w-full text-left rounded-lg p-3 transition-all border ${
              isSelected
                ? 'bg-purple-500/20 border-purple-500/30'
                : isDark
                  ? 'bg-white/3 border-white/8 hover:bg-purple-500/10 hover:border-purple-500/20'
                  : 'bg-black/3 border-black/8 hover:bg-purple-500/5 hover:border-purple-500/20'
            }`}
          >
            <div className="flex items-start gap-2">
              <BookOpen className="w-4 h-4 flex-shrink-0 text-sky-400 mt-0.5" />
              <div className="min-w-0 flex-1">
                <div className={`text-[13px] font-semibold leading-snug truncate ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
                  {paper.title}
                </div>
                <div className={`text-[11px] mt-1 truncate ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                  {paper.authors || 'Unknown authors'}
                  {paper.year && paper.year > 0 ? ` · ${paper.year}` : ''}
                </div>
                {tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {tags.map(tag => (
                      <span
                        key={`${paper.paper_id}-${tag}`}
                        className={`text-[10px] px-1.5 py-0.5 rounded ${isDark ? 'bg-white/8 text-gray-300' : 'bg-black/5 text-gray-600'}`}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                <div className={`text-[10px] mt-2 ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>
                  {paper.claim_count ?? 0} claim{(paper.claim_count ?? 0) === 1 ? '' : 's'}
                  {' · '}
                  {paper.limitation_count ?? 0} limitation{(paper.limitation_count ?? 0) === 1 ? '' : 's'}
                  {' · '}
                  {paper.contribution_count ?? 0} contribution{(paper.contribution_count ?? 0) === 1 ? '' : 's'}
                </div>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
