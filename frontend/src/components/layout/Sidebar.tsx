
import {
    BrainCircuit,
    LayoutDashboard,
    Files,
    Search,
    MessageSquare,
    Settings,
    X,
} from "lucide-react";

import { NavLink } from "react-router-dom";

type SidebarProps = {
    isOpen: boolean;
    onClose: () => void;
};

const navigation = [
    {
        label: "Dashboard",
        path: "/",
        icon: LayoutDashboard,
    },
    {
        label: "Documents",
        path: "/documents",
        icon: Files,
    },
    {
        label: "Semantic Search",
        path: "/search",
        icon: Search,
    },
    {
        label: "AI Chat",
        path: "/chat",
        icon: MessageSquare,
    },
    {
        label: "Settings",
        path: "/settings",
        icon: Settings,
    },
];

export function Sidebar({
    isOpen,
    onClose,
}: SidebarProps) {
    return (
        <>
            {isOpen && (
                <button
                    type="button"
                    aria-label="Close navigation"
                    onClick={onClose}
                    className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden"
                />
            )}

            <aside
                id="app-sidebar"
                className={`
          fixed inset-y-0 left-0 z-50 w-64
          border-r border-slate-200 bg-white
          transition-transform duration-200
          lg:static lg:translate-x-0
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
        `}
            >
                <div className="flex h-18 items-center justify-between border-b border-slate-200 px-5 py-4">
                    <div className="flex items-center gap-3">
                        <div className="rounded-lg bg-indigo-600 p-2 text-white">
                            <BrainCircuit size={22} />
                        </div>

                        <div>
                            <h1 className="text-sm font-bold text-slate-900">
                                Enterprise RAG
                            </h1>
                            <p className="text-xs text-slate-500">
                                AI Workspace
                            </p>
                        </div>
                    </div>

                    <button
                        type="button"
                        aria-label="Close sidebar"
                        onClick={onClose}
                        className="rounded-md p-1 text-slate-500 lg:hidden"
                    >
                        <X size={20} />
                    </button>
                </div>

                <nav
                    aria-label="Main navigation"
                    className="space-y-1 p-3"
                >
                    {navigation.map((item) => {
                        const Icon = item.icon;

                        return (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                end={item.path === "/"}
                                onClick={onClose}
                                className={({ isActive }) =>
                                    [
                                        "flex items-center gap-3 rounded-lg",
                                        "px-3 py-2.5 text-sm font-medium",
                                        "transition-colors",
                                        isActive
                                            ? "bg-indigo-50 text-indigo-700"
                                            : "text-slate-600 hover:bg-slate-100",
                                    ].join(" ")
                                }
                            >
                                <Icon size={19} />
                                {item.label}
                            </NavLink>
                        );
                    })}
                </nav>
            </aside>
        </>
    );
}
