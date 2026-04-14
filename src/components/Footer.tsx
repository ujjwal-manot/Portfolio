import Link from "next/link";
import { Mail, Linkedin } from "lucide-react";

export function Footer() {
    return (
        <footer className="border-t border-border mt-auto bg-white/50 backdrop-blur-sm">
            <div className="max-w-7xl mx-auto px-6 py-8">
                <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="text-sm text-muted">
                        © {new Date().getFullYear()} Dr. Rohan Katti. All rights reserved.
                    </div>

                    <div className="flex items-center gap-6">
                        <Link
                            href="mailto:rohan.katti@bennett.edu.in"
                            className="inline-flex items-center gap-2 text-sm text-muted hover:text-primary transition-colors group"
                        >
                            <Mail className="h-4 w-4 group-hover:scale-110 transition-transform" />
                            <span>rohan.katti@bennett.edu.in</span>
                        </Link>

                        <Link
                            href="https://www.linkedin.com/in/rohan-katti-b562699b/"
                            target="_blank"
                            className="inline-flex items-center gap-2 text-sm text-muted hover:text-[#0077b5] transition-colors group"
                        >
                            <Linkedin className="h-4 w-4 group-hover:scale-110 transition-transform" />
                            <span>LinkedIn</span>
                        </Link>
                    </div>
                </div>
            </div>
        </footer>
    );
}
