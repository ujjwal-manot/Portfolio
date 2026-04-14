export default function StudentsPage() {
    const currentStudents = [
        {
            name: "Agastasya Dahiya",
            batch: "2021-25",
            project: "Hand Gesture Recognition Using Edge AI and Wearable Sensors",
            publications: 2,
            color: "from-blue-500 to-blue-600",
        },
        {
            name: "Dhruv Wadhwa",
            batch: "2021-25",
            project: "Design and Implementation of a RISC-V Core on FPGA for DSP Applications",
            publications: 1,
            color: "from-purple-500 to-purple-600",
        },
        {
            name: "Siddharth Singh",
            batch: "2020-24",
            project: "Quantum Analysis of Photonic Devices",
            publications: 2,
            color: "from-indigo-500 to-indigo-600",
        },

        {
            name: "Ujjwal Manot",
            batch: "2023-27",
            project: "Working on non-invasive medical device projects and ML model integration. Also working on Wi-Clip project for human activity mapping without line of sight.",
            publications: 0,
            color: "from-amber-500 to-amber-600",
        },
        {
            name: "Aman Kumar",
            batch: "2022-26",
            project: "Major project on Quantum computing; emulating quantum logic gates and Quantum Fourier Transform on FPGA.",
            publications: 0,
            color: "from-emerald-500 to-emerald-600",
        },
    ];

    const alumni: any[] = [];

    const achievements = [
        {
            students: "Third-Year ECE Students (2021-25 Batch)",
            award: "3rd Position, All India STMicroelectronics Innovation Fair",
            project: "Hand gesture recognition for smart wearables using edge AI",
            date: "March 2024",
            color: "border-amber-300 bg-amber-50",
        },
        {
            students: "Third-Year ECE Students (2018-23 Batch)",
            award: "Best Hardware Design Project, ECE Department",
            project: "IoT-based smart elevator system",
            date: "May 2022",
            color: "border-teal-300 bg-teal-50",
        },
    ];

    return (
        <div className="page-bg-students min-h-screen">
            <div className="max-w-7xl mx-auto px-4 md:px-8 lg:px-12 py-16">
                <div className="animate-fade-in-up">
                    <h1 className="text-3xl font-bold mb-2">Students</h1>
                    <p className="text-muted mb-12 max-w-2xl">
                        I take great pride in mentoring undergraduate researchers and guiding them towards
                        impactful projects and peer-reviewed publications.
                    </p>
                </div>

                {/* Stats */}
                <section className="mb-16">
                    <div className="flex flex-wrap justify-center gap-8 p-8 rounded-2xl border-2 border-blue-200 bg-blue-50/50">
                        <div className="text-center">
                            <div className="text-4xl font-bold text-primary">5</div>
                            <div className="text-sm text-muted mt-1">Currently Mentoring</div>
                        </div>
                        <div className="text-center">
                            <div className="text-4xl font-bold" style={{ color: '#8b5cf6' }}>7</div>
                            <div className="text-sm text-muted mt-1">Projects Supervised</div>
                        </div>
                        <div className="text-center">
                            <div className="text-4xl font-bold" style={{ color: '#14b8a6' }}>6</div>
                            <div className="text-sm text-muted mt-1">Student Co-authored Papers</div>
                        </div>
                    </div>
                </section>

                {/* Current Students */}
                <section className="mb-16">
                    <h2 className="section-title">Current Research Students</h2>
                    <div className="grid md:grid-cols-2 gap-6">
                        {currentStudents.map((student, idx) => (
                            <div key={idx} className="p-6 border border-border rounded-2xl card-hover overflow-hidden relative">
                                <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${student.color}`}></div>
                                <div className="flex items-center justify-between mb-4">
                                    <div className={`w-12 h-12 rounded-full bg-[var(--secondary)] text-[var(--primary)] flex items-center justify-center font-bold text-lg`}>
                                        {student.name.charAt(0)}
                                    </div>
                                </div>
                                <h3 className="font-bold text-xl mb-1">{student.name}</h3>
                                <p className="text-sm text-muted mb-4">B.Tech. {student.batch}</p>
                                <div className="p-3 bg-secondary rounded-lg">
                                    <p className="text-sm font-medium">Project</p>
                                    <p className="text-sm text-muted">{student.project}</p>
                                </div>
                                {student.publications > 0 && (
                                    <p className="text-sm mt-4 text-primary font-medium">
                                        📄 {student.publications} publication{student.publications > 1 ? "s" : ""}
                                    </p>
                                )}
                            </div>
                        ))}
                    </div>
                </section>

                {/* Alumni */}
                {alumni.length > 0 && (
                    <section className="mb-16">
                        <h2 className="section-title">Past Students</h2>
                        <div className="space-y-3">
                            {alumni.map((student, idx) => (
                                <div key={idx} className="flex items-center justify-between p-4 border border-border rounded-xl card-hover">
                                    <div className="flex items-center gap-4">
                                        <div className="w-10 h-10 rounded-full bg-[var(--secondary)] text-[var(--primary)] flex items-center justify-center font-bold">
                                            {student.name.charAt(0)}
                                        </div>
                                        <div>
                                            <h3 className="font-semibold">{student.name}</h3>
                                            <p className="text-sm text-muted">{student.project}</p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <span className="tag tag-purple">B.Tech. {student.batch}</span>
                                        {student.publications > 0 && (
                                            <p className="text-xs text-muted mt-1">{student.publications} paper{student.publications > 1 ? "s" : ""}</p>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Achievements */}
                <section>
                    <h2 className="section-title">Student Achievements</h2>
                    <div className="space-y-4">
                        {achievements.map((item, idx) => (
                            <div key={idx} className={`flex gap-4 p-5 border-2 rounded-xl card-hover ${item.color}`}>
                                <div className="text-3xl">🏆</div>
                                <div>
                                    <h3 className="font-bold text-lg">{item.award}</h3>
                                    <p className="text-sm text-muted mt-1">{item.students}</p>
                                    <p className="text-sm mt-2">Project: <em>{item.project}</em></p>
                                    <p className="text-xs text-muted mt-2">{item.date}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            </div>
        </div>
    );
}
