export default function ResearchPage() {
    return (
        <div className="page-bg-research min-h-screen">
            <div className="max-w-7xl mx-auto px-4 md:px-8 lg:px-12 py-16">
                <div className="animate-fade-in-up">
                    <h1 className="text-3xl font-bold mb-2">Research</h1>
                    <p className="text-muted mb-12 max-w-2xl">
                        My research focuses on evaluating the unique properties of light to develop
                        efficient, high-speed solutions for communication and computation. I am particularly
                        interested in the intersection of photonics and applied electronics. I am also involved in exploring implementation of signal processing algorithms on FPGAs and quantum computing.
                    </p>
                </div>

                {/* Research Areas */}
                <section className="mb-16">
                    <h2 className="section-title">Core Research Themes</h2>
                    <div className="grid md:grid-cols-2 gap-6">
                        <div className="p-6 border border-border rounded-xl card-hover accent-blue">
                            <h3 className="font-semibold text-lg mb-3 text-primary">Microwave Photonics</h3>
                            <p className="text-muted text-sm leading-relaxed">
                                Developing photonics-assisted techniques for generating high-frequency RF and
                                millimetre-wave signals for beyond-5G wireless systems. This utilises the advantages
                                of photonics, broad bandwidth, low loss, and immunity to electromagnetic interference.
                            </p>
                        </div>
                        <div className="p-6 border border-border rounded-xl card-hover accent-purple">
                            <h3 className="font-semibold text-lg mb-3" style={{ color: '#8b5cf6' }}>Silicon Photonics</h3>
                            <p className="text-muted text-sm leading-relaxed">
                                Designing and modelling photonic integrated circuits on silicon-on-insulator platforms,
                                with particular emphasis on microring resonators for filtering, modulation, and optical
                                delay line applications in compact, scalable configurations.
                            </p>
                        </div>
                        <div className="p-6 border border-border rounded-xl card-hover accent-teal">
                            <h3 className="font-semibold text-lg mb-3" style={{ color: '#14b8a6' }}>All-Optical Computing</h3>
                            <p className="text-muted text-sm leading-relaxed">
                                Investigating all-optical logic gates and arithmetic circuits by exploiting
                                nonlinear optical effects in Mach-Zehnder interferometers, enabling ultrafast
                                computation without the bottlenecks of electronic domain translation.
                            </p>
                        </div>
                        <div className="p-6 border border-border rounded-xl card-hover accent-amber">
                            <h3 className="font-semibold text-lg mb-3" style={{ color: '#f59e0b' }}>Photonic Integrated Circuits</h3>
                            <p className="text-muted text-sm leading-relaxed">
                                Analysing complex photonic structures such as SCISSOR, CROW, and PANDA ring resonator
                                topologies for implementing integrated optical delay lines and advanced signal processing
                                functionalities on chip.
                            </p>
                        </div>
                        <div className="p-6 border border-border rounded-xl card-hover accent-blue">
                            <h3 className="font-semibold text-lg mb-3 text-primary">Signal processing implementation on FPGA</h3>
                            <p className="text-muted text-sm leading-relaxed">
                                Exploring the implementation of advanced signal processing algorithms on FPGA platforms.
                            </p>
                        </div>
                        <div className="p-6 border border-border rounded-xl card-hover accent-purple">
                            <h3 className="font-semibold text-lg mb-3" style={{ color: '#8b5cf6' }}>Quantum computing</h3>
                            <p className="text-muted text-sm leading-relaxed">
                                Implementing quantum computing concepts on FPGA.
                            </p>
                        </div>
                    </div>
                </section>

                {/* Funded Research */}
                <section className="mb-16">
                    <h2 className="section-title">Funded Research</h2>
                        <div className="card-hover border-l-4 accent-teal p-6 rounded-lg">
                            <div className="flex items-start justify-between gap-4 mb-3">
                                <h3 className="font-semibold text-lg">
                                    Modelling of Mach-Zehnder Interferometer-Based Modulators for Arbitrary Waveform Generation
                                </h3>
                            <span className="tag tag-teal whitespace-nowrap">Active</span>
                        </div>
                        <p className="text-muted text-sm mb-4">
                            This project investigates the application of MZI-based electro-optic modulators for
                            synthesising arbitrary microwave waveforms using photonic techniques, with potential
                            applications in radar, electronic warfare, and next-generation wireless systems.
                        </p>
                            <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2 sm:gap-6 text-sm text-muted">
                                <span><strong>Funding:</strong> ₹10 Lakhs</span>
                                <span><strong>Duration:</strong> 2024-2026</span>
                                <span><strong>Agency:</strong> Bennett University SEED Grant</span>
                            </div>
                    </div>
                </section>

                {/* Research Metrics */}
                <section className="mb-16">
                    <h2 className="section-title">Research Supervision</h2>
                    <div className="grid grid-cols-2 md:grid-cols-2 gap-4">
                        <div className="text-center p-5 border border-border rounded-xl card-hover">
                            <div className="text-2xl font-bold text-primary">3</div>
                            <div className="text-sm text-muted mt-1">Current B.Tech. Projects</div>
                        </div>
                        <div className="text-center p-5 border border-border rounded-xl card-hover">
                            <div className="text-2xl font-bold" style={{ color: '#8b5cf6' }}>7</div>
                            <div className="text-sm text-muted mt-1">B.Tech. Projects Supervised</div>
                        </div>
                    </div>
                </section>

                {/* Tools */}
                <section>
                    <h2 className="section-title">Simulation Tools & Software</h2>
                    <div className="grid md:grid-cols-2 gap-8">
                        <div className="p-5 border border-border rounded-xl card-hover">
                            <h3 className="font-semibold mb-4 text-primary">Photonics Design</h3>
                            <ul className="space-y-2 text-sm text-muted">
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 flex-shrink-0 rounded-full" style={{ background: 'var(--primary)' }}></span>OptiSystem</li>
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 flex-shrink-0 rounded-full" style={{ background: '#8b5cf6' }}></span>RSoft FullWAVE, OptSim, OptSim Circuit</li>
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 flex-shrink-0 rounded-full" style={{ background: '#14b8a6' }}></span>Lumerical Interconnect</li>
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 flex-shrink-0 rounded-full" style={{ background: '#f59e0b' }}></span>MATLAB</li>
                            </ul>
                        </div>
                        <div className="p-5 border border-border rounded-xl card-hover">
                            <h3 className="font-semibold mb-4" style={{ color: '#8b5cf6' }}>General Purpose</h3>
                            <ul className="space-y-2 text-sm text-muted">
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 flex-shrink-0 rounded-full" style={{ background: 'var(--primary)' }}></span>LaTeX for academic writing</li>
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 flex-shrink-0 rounded-full" style={{ background: '#14b8a6' }}></span>TINA for circuit analysis</li>
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 flex-shrink-0 rounded-full" style={{ background: '#f59e0b' }}></span>Python for data analysis</li>
                            </ul>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
}
