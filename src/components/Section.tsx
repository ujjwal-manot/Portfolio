"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface SectionProps {
    id?: string;
    title?: string;
    description?: string;
    children: React.ReactNode;
    className?: string;
    delay?: number;
}

export function Section({ id, title, description, children, className, delay = 0 }: SectionProps) {
    return (
        <section id={id} className={cn("py-16 md:py-24 lg:py-32 relative", className)}>
            {/* Subtle background decoration */}
            <div className="absolute inset-0 grid-pattern opacity-50 pointer-events-none" />

            <motion.div
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.6, delay }}
                className="container relative px-4 md:px-6"
            >
                {(title || description) && (
                    <div className="mb-12 md:mb-16 text-center md:text-left">
                        {title && (
                            <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl gradient-text inline-block">
                                {title}
                            </h2>
                        )}
                        {description && (
                            <p className="mt-4 max-w-[700px] text-muted-foreground md:text-xl leading-relaxed">
                                {description}
                            </p>
                        )}
                    </div>
                )}
                {children}
            </motion.div>
        </section>
    );
}
