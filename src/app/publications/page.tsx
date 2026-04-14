"use client";

import { useState } from "react";
import Link from "next/link";
import { ExternalLink, FileText, BookOpen, Presentation, Search } from "lucide-react";

// Helper to create Google Scholar search link
const scholarSearch = (title: string) =>
    `https://scholar.google.com/scholar?q=${encodeURIComponent(`"${title}"`)}`;

const patents = [
    {
        authors: "Shanthi Prince and Rohan Katti",
        title: "System and Method for Generating Multiple Mutually Different Microwave Waveforms",
        info: "Indian Patent No. 532570",
        status: "Granted",
        date: "October 2024",
    },
    {
        authors: "Shanthi Prince and Rohan Katti",
        title: "System and Method for Nyquist Pulse Generation Based on Microring Resonator",
        info: "Application No. 201841048886",
        status: "Filed",
        date: "December 2018",
    },
];

const journals = [
    {
        authors: "Siddharth Singh and Rohan Katti",
        title: "Analysis of Photon Flux Dynamics in a Microring Resonator operating under Single-Photon Pulsed Excitation",
        venue: "Physica Scripta",
        year: "2026",
        volume: "Accepted",
        tags: ["Q2", "IF: 2.6"],
    },
    {
        authors: "A. Dahiya, R. Katti, and L. G. Occhipinti",
        title: "Real-Time Hand Gesture Classification Using Infrared Sensor Arrays-Based Wearable Bracelet",
        venue: "IEEE Sensors Letters",
        year: "2025",
        volume: "vol. 9, no. 6",
        tags: ["Q2", "IF: 2.2"],
    },
    {
        authors: "A. Dahiya, D. Wadhwa, R. Katti, and L. G. Occhipinti",
        title: "Efficient Hand Gesture Recognition Using AI and IMU-Based Wearable Device",
        venue: "IEEE Sensors Letters",
        year: "2024",
        volume: "vol. 8, no. 12",
        tags: ["Q2", "IF: 2.2"],
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Millimetre Wave Generation Based on Coupling Coefficients of Silicon Microring Resonator",
        venue: "Physica Scripta",
        year: "2024",
        volume: "vol. 99",
        tags: ["Q2", "IF: 2.6"],
    },
    {
        authors: "S. Singh and R. Katti",
        title: "Quantum Analysis of Mach-Zehnder Interferometer with Single-Photon Gaussian Packets",
        venue: "Journal of the Optical Society of America B",
        year: "2024",
        volume: "vol. 41, no. 2",
        tags: ["Q2", "IF: 1.8"],
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Reconfigurable Photonic System for Millimetre-Wave Generation for 5G Applications",
        venue: "Optik",
        year: "2021",
        volume: "vol. 248",
        tags: ["Q2", "IF: 3.1"],
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Terahertz Signal Generation Based on Microwave Photonic System with Microring Resonator",
        venue: "Microwave and Optical Technology Letters",
        year: "2020",
        volume: "vol. 62, no. 8",
        tags: ["Q2", "IF: 1.0"],
    },
    {
        authors: "R. Katti and S. Prince",
        title: "A Survey on the Role of Photonic Technologies in 5G Communication Systems",
        venue: "Photonic Network Communications",
        year: "2019",
        volume: "vol. 38, no. 2",
        tags: ["Q3", "IF: 1.8"],
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Microring Resonator-Based Photonic System for Terahertz Signal Generation",
        venue: "Photonic Network Communications",
        year: "2019",
        volume: "vol. 38, no. 1",
        tags: ["Q3", "IF: 1.8"],
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Microring Resonator-Based Logic Module for All-Optical Information Processing",
        venue: "Journal of Modern Optics",
        year: "2018",
        volume: "vol. 65, no. 15",
        tags: ["Q3", "IF: 1.2"],
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Photonic Delay Lines Based on Silicon Coupled Resonator Optical Waveguide Structures",
        venue: "Silicon",
        year: "2018",
        volume: "vol. 10, no. 6",
        tags: ["Q2", "IF: 2.8"],
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Analysis of Serial and Parallel Cascaded Microring Resonators: An FDTD Approach",
        venue: "Optik",
        year: "2018",
        volume: "vol. 152",
        tags: ["Q2", "IF: 3.1"],
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Ultrafast Optical Binary-to-Gray Code Conversion in Mach-Zehnder Interferometer",
        venue: "Optical Engineering",
        year: "2017",
        volume: "vol. 56, no. 2",
        tags: ["Q2", "IF: 1.1"],
    },
    {
        authors: "R. Katti and S. Prince",
        title: "All-Optical 3×3 Reversible Logic Gate Using Mach-Zehnder Interferometer",
        venue: "Optical and Quantum Electronics",
        year: "2016",
        volume: "vol. 48, no. 63",
        tags: ["Q2", "IF: 3.3"],
    },
];

const conferences = [
    {
        authors: "R. Katti and A. Yadav",
        title: "Photonic Generation of 0.1-0.15 THz Band Based on RF Generator Train",
        venue: "IEEE WRAP",
        location: "IIIT Allahabad",
        year: "2023",
    },
    {
        authors: "R. Katti",
        title: "Digitally Encoded Arbitrary Microwave Waveform Generation Assisted by Photonics",
        venue: "IEEE WRAP",
        location: "IIIT Allahabad",
        year: "2023",
    },
    {
        authors: "S. Singh and R. Katti",
        title: "Analysis of Microring Resonator with Fock State Wavepackets",
        venue: "IEEE WRAP",
        location: "IIIT Allahabad",
        year: "2023",
        award: "Best Paper Award",
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Simulation Analysis of Microring Resonator in Möbius Topology",
        venue: "IEEE NUSOD",
        location: "Turin, Italy",
        year: "2022",
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Damped Sinusoidal and Ultra-Wideband Waveforms via Optoelectronic Approach",
        venue: "SPIE Photonics Europe",
        location: "France",
        year: "2020",
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Microwave Photonic System for Ultra-Wideband Waveform Generation",
        venue: "IEEE WRAP",
        location: "IIT Guwahati",
        year: "2019",
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Design and Modelling of PANDA Ring Resonator Structure",
        venue: "IEEE ICP",
        location: "Malaysia",
        year: "2018",
    },
    {
        authors: "R. Katti and S. Prince",
        title: "SCISSOR Structure for Nanophotonic Integrated Delay Lines",
        venue: "IEEE WRAP",
        location: "IIT Delhi",
        year: "2017",
    },
    {
        authors: "R. Katti and S. Prince",
        title: "All-Optical Binary to Two's Complement Conversion Using Microring Resonators",
        venue: "OSA Photonics",
        location: "IIT Kanpur",
        year: "2016",
    },
    {
        authors: "R. Katti and S. Prince",
        title: "Reversible All-Optical Multiplexer Using Mach-Zehnder Interferometer",
        venue: "IEEE SPICES",
        location: "Kerala",
        year: "2015",
    },
];

export default function PublicationsPage() {
    const [query, setQuery] = useState("");

    const filterItem = (item: any) => {
        const searchStr = `${item.title} ${item.authors} ${item.venue} ${item.year}`.toLowerCase();
        return searchStr.includes(query.toLowerCase());
    };

    const filteredJournals = journals.filter(filterItem);
    const filteredConferences = conferences.filter(filterItem);
    const filteredPatents = patents.filter(filterItem);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") {
            // Find the first available result across categories
            const allResults = [...filteredJournals, ...filteredConferences, ...filteredPatents];
            if (allResults.length > 0) {
                const firstResult = allResults[0];
                const url = scholarSearch(firstResult.title);
                window.open(url, "_blank");
            }
        }
    };

    return (
        <div className="page-bg-publications min-h-screen">
            <div className="max-w-7xl mx-auto px-4 md:px-8 lg:px-12 py-16">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8 animate-fade-in-up">
                    <div>
                        <h1 className="text-3xl font-bold mb-2">Publications</h1>
                        <p className="text-muted max-w-xl">
                            A comprehensive list of my peer-reviewed research contributions.
                        </p>
                    </div>
                    <div className="flex gap-6 text-sm">
                        <div className="text-center">
                            <div className="text-2xl font-bold text-primary">{journals.length}</div>
                            <div className="text-muted">Journals</div>
                        </div>
                        <div className="text-center">
                            <div className="text-2xl font-bold" style={{ color: '#8b5cf6' }}>{conferences.length}</div>
                            <div className="text-muted">Conferences</div>
                        </div>
                        <div className="text-center">
                            <div className="text-2xl font-bold" style={{ color: '#14b8a6' }}>{patents.length}</div>
                            <div className="text-muted">Patents</div>
                        </div>
                    </div>
                </div>

                {/* Search Bar */}
                <div className="relative mb-12 animate-fade-in-up">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search className="h-5 w-5 text-muted" />
                    </div>
                    <input
                        type="text"
                        className="block w-full pl-10 pr-3 py-3 border border-border rounded-lg leading-5 bg-card placeholder-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition duration-150 ease-in-out shadow-sm"
                        placeholder="Search papers by title, author, or venue... (Press Enter to open first result)"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
                    />
                </div>

                {filteredPatents.length > 0 && (
                    <section className="mb-16 animate-fade-in">
                        <h2 className="section-title flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            Patents
                        </h2>
                        <div className="grid md:grid-cols-2 gap-4">
                            {filteredPatents.map((patent, idx) => (
                                <div key={idx} className="p-5 border border-border rounded-xl card-hover">
                                    <div className="flex items-start justify-between gap-3 mb-3">
                                        <span className={`tag ${patent.status === "Granted" ? "tag-teal" : "tag-amber"}`}>
                                            {patent.status}
                                        </span>
                                        <span className="text-sm text-muted">{patent.date}</span>
                                    </div>
                                    <h3 className="font-semibold mb-2">{patent.title}</h3>
                                    <p className="text-sm text-muted mb-1">{patent.authors}</p>
                                    <p className="text-sm">{patent.info}</p>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {filteredJournals.length > 0 && (
                    <section className="mb-16 animate-fade-in">
                        <h2 className="section-title flex items-center gap-2">
                            <BookOpen className="h-4 w-4" />
                            Journal Articles ({filteredJournals.length})
                        </h2>
                        <div className="space-y-0">
                            {filteredJournals.map((pub, idx) => (
                                <div key={idx} className="pub-item group">
                                    <div className="flex items-start gap-4">
                                        <span className="text-sm font-bold text-primary min-w-[40px]">{pub.year}</span>
                                        <div className="flex-1">
                                            <a
                                                href={scholarSearch(pub.title)}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="font-medium hover:text-primary transition-colors inline-flex items-center gap-1"
                                            >
                                                {pub.title}
                                                <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                                            </a>
                                            <p className="text-sm text-muted mt-1">{pub.authors}</p>
                                            <p className="text-sm mt-1">
                                                <em>{pub.venue}</em>, {pub.volume}
                                            </p>
                                            <div className="flex gap-2 mt-2">
                                                {pub.tags.map((tag, i) => (
                                                    <span key={i} className={`tag text-xs ${i === 0 ? 'tag-purple' : 'tag-teal'}`}>{tag}</span>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {filteredConferences.length > 0 && (
                    <section className="animate-fade-in">
                        <h2 className="section-title flex items-center gap-2">
                            <Presentation className="h-4 w-4" />
                            Conference Papers ({filteredConferences.length})
                        </h2>
                        <div className="space-y-0">
                            {filteredConferences.map((pub, idx) => (
                                <div key={idx} className="pub-item group">
                                    <div className="flex items-start gap-4">
                                        <span className="text-sm font-bold min-w-[40px]" style={{ color: '#8b5cf6' }}>{pub.year}</span>
                                        <div className="flex-1">
                                            <div className="flex items-start gap-2 flex-wrap">
                                                <a
                                                    href={scholarSearch(pub.title)}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="font-medium hover:text-primary transition-colors inline-flex items-center gap-1"
                                                >
                                                    {pub.title}
                                                    <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                                                </a>
                                                {pub.award && (
                                                    <span className="tag tag-rose text-xs whitespace-nowrap">🏆 {pub.award}</span>
                                                )}
                                            </div>
                                            <p className="text-sm text-muted mt-1">{pub.authors}</p>
                                            <p className="text-sm mt-1">
                                                <em>{pub.venue}</em>, {pub.location}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {filteredJournals.length === 0 && filteredConferences.length === 0 && filteredPatents.length === 0 && (
                    <div className="text-center py-20 animate-fade-in">
                        <p className="text-muted text-lg">No publications found matching "{query}"</p>
                    </div>
                )}
            </div>
        </div>
    );
}
