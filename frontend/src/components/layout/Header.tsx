import { Menu, CircleHelp, UserRound } from "lucide-react";
import { useLocation } from "react-router-dom";

type HeaderProps = {
    onMenuClick: () => void;
};

const pageTitles: Record<string, string> = {
    "/": "Dashboard",
    "/documents": "Documents",
    "/search": "Semantic Search",
    "/chat": "AI Chat",
    "/settings": "Settings",
};

export function Header({ onMenuClick }: HeaderProps) {
    const location = useLocation();

    const title = pageTitles[location.pathname] ?? "Enterprise RAG";

    return (
        <header className="flex h-18 items-center justify-between border-b border-slate-200 bg-white px-6">
            <div className="flex items-center gap-3">
                <button
                    type="button"
                    aria-label="Open navigation"
                    aria-controls="app-sidebar"
                    onClick={onMenuClick}
                    className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
                >
                    <Menu size={22} />
                </button>

                <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
            </div>

            <div className="flex items-center gap-4">
                <CircleHelp size={19} aria-hidden="true" className="text-slate-400" />

                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-slate-600">
                    <UserRound size={19} />
                </div>
            </div>
        </header>
    );
}
