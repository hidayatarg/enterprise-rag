
import { useEffect, useState } from "react";
import { healthApi } from "../api/healthApi";

type BackendState =
    | "checking"
    | "online"
    | "offline";

export function BackendStatus() {
    const [status, setStatus] = useState<BackendState>("checking");

    useEffect(() => {

        // Only update state while this component is mounted.
        let active = true;

        async function checkHealth() {
            try {
                const response = await healthApi.getStatus();

                if (active) {
                    setStatus(
                        response.status.toLowerCase() === "ok" ||
                            response.status.toLowerCase() === "healthy"
                            ? "online"
                            : "offline",
                    );
                }
            } catch {
                if (active) {
                    setStatus("offline");
                }
            }
        }

        void checkHealth();

        return () => {
            active = false;
        };
    }, []);

    const labels = {
        checking: "Checking backend...",
        online: "Backend online",
        offline: "Backend offline",
    };

    const colors = {
        checking: "bg-amber-400",
        online: "bg-emerald-500",
        offline: "bg-red-500",
    };

    return (
        <div
            role="status"
            className="flex items-center gap-2 text-sm text-slate-600"
        >
            <span
                className={`h-2.5 w-2.5 rounded-full ${colors[status]}`}
            />

            {labels[status]}
        </div>
    );
}
