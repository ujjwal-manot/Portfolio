"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

interface CardProps {
    title: string;
    subtitle?: string;
    description?: string;
    tags?: string[];
    href?: string;
    date?: string;
    className?: string;
}

export function Card({ title, subtitle, description, tags, href, date, className }: CardProps) {
    const content = (
        <motion.div
            whileHover={{ y: -5, scale: 1.02 }}
            transition={{ type: "spring", stiffness: 300 }}
            className={cn(
                "group relative h-full overflow-hidden rounded-2xl glass glow-on-hover transition-all",
                className
            )}
        >
            {/* Gradient border effect */}
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary/20 via-purple-500/10 to-pink-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />

            <div className="relative flex flex-col h-full p-6">
                {date && (
                    <span className="mb-3 inline-flex items-center rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary w-fit">
                        {date}
                    </span>
                )}
                <div className="flex items-start justify-between gap-4">
                    <h3 className="text-xl font-bold leading-tight group-hover:text-primary transition-colors">
                        {title}
                    </h3>
                    {href && (
                        <div className="p-2 rounded-full bg-primary/10 opacity-0 group-hover:opacity-100 transition-all">
                            <ArrowUpRight className="h-4 w-4 text-primary" />
                        </div>
                    )}
                </div>

                {subtitle && (
                    <p className="mt-2 text-sm font-medium text-primary/80">
                        {subtitle}
                    </p>
                )}

                {description && (
                    <p className="mt-4 text-muted-foreground flex-1 leading-relaxed">
                        {description}
                    </p>
                )}

                {tags && tags.length > 0 && (
                    <div className="mt-6 flex flex-wrap gap-2">
                        {tags.map((tag) => (
                            <span
                                key={tag}
                                className="inline-flex items-center rounded-full bg-secondary/50 px-3 py-1 text-xs font-medium text-foreground/80 transition-colors hover:bg-primary/20 hover:text-primary"
                            >
                                {tag}
                            </span>
                        ))}
                    </div>
                )}
            </div>
        </motion.div>
    );

    if (href) {
        return (
            <Link href={href} target="_blank" rel="noopener noreferrer" className="block h-full">
                {content}
            </Link>
        );
    }

    return content;
}
