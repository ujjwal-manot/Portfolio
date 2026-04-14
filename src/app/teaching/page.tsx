export default function TeachingPage() {
    const courses = [
        { name: "Digital Signal Processing", level: "UG", color: "tag-primary" },
        { name: "Signals and Systems", level: "UG", color: "tag-purple" },
        { name: "Probability Theory and Stochastic Processes", level: "UG", color: "tag-teal" },
        { name: "Analog and Digital Communications", level: "UG", color: "tag-amber" },
        { name: "Wireless Communications", level: "UG", color: "tag-primary" },
        { name: "Information Theory and Coding", level: "UG", color: "tag-purple" },
        { name: "Advanced Digital Signal Processing", level: "UG", color: "tag-rose" },
    ];

    const talks = [
        {
            title: "Optica Outreach Programme",
            event: "Optica Outreach",
            venue: "Om Public School",
            date: "11 September 2025",
        },
        {
            title: "Role of Photonic Technologies in Next-Generation Communication Systems",
            event: "International Day of Light Celebrations",
            venue: "SRM Institute of Science and Technology",
            date: "May 2021",
        },
        {
            title: "Modelling of SOI Devices for Nanophotonic Applications",
            event: "Nanophotonics Symposium",
            venue: "SRM Research Institute",
            date: "January 2020",
        },
        {
            title: "Explore Optics: Hands-On Optical Experiments",
            event: "Science Outreach Programme",
            venue: "S.P. Koil Government Higher Secondary School",
            date: "August 2019",
        },
        {
            title: "Academic Writing with LaTeX",
            event: "OSA Student Chapter Workshop",
            venue: "SRM IST",
            date: "January 2019",
        },
        {
            title: "Photonic Device Modelling Using MATLAB",
            event: "DRDO-Sponsored Workshop on Photonic Devices",
            venue: "SRM IST",
            date: "July 2018",
        },
    ];

    const responsibilities = [
        { role: "Department Secretary", desc: "Coordinating faculty meetings and institutional records", color: "bg-blue-500" },
        { role: "B.Tech. Project Coordinator", desc: "Overseeing final-year project evaluations", color: "bg-purple-500" },
        { role: "NEP Curriculum Committee", desc: "Designing ECE curriculum for 2025-29 cohort", color: "bg-teal-500" },
        { role: "Faculty Mentor (2023-27 Batch)", desc: "Academic guidance to undergraduates", color: "bg-amber-500" },
        { role: "Bennett Hatchery HUM Club", desc: "Technical mentorship for startups", color: "bg-pink-500" },
    ];

    return (
        <div className="page-bg-teaching min-h-screen">
            <div className="max-w-7xl mx-auto px-4 md:px-8 lg:px-12 py-16">
                <div className="animate-fade-in-up">
                    <h1 className="text-3xl font-bold mb-2">Teaching</h1>
                    <p className="text-muted mb-12 max-w-2xl">
                        I am committed to nurturing the next generation of engineers through innovative teaching methodologies,
                        hands-on projects, and active mentorship.
                    </p>
                </div>

                {/* Teaching Experience */}
                <section className="mb-16">
                    <h2 className="section-title">Academic Positions</h2>
                    <div className="relative">
                        <div className="timeline-item">
                            <div className="flex items-center gap-3 mb-1">
                                <span className="font-semibold text-lg">Assistant Professor</span>
                                <span className="tag tag-teal">Current</span>
                            </div>
                            <div className="text-[var(--primary)]">Bennett University, Greater Noida</div>
                            <div className="text-sm text-muted">September 2020 - Present</div>
                            <p className="text-sm mt-2 text-muted">
                                Department of ECE, School of Engineering and Applied Sciences
                            </p>
                        </div>
                        <div className="timeline-item">
                            <div className="font-semibold text-lg">Teaching Assistant</div>
                            <div style={{ color: "#8b5cf6" }}>SRM Institute of Science and Technology, Chennai</div>
                            <div className="text-sm text-muted">January 2016 - March 2020</div>
                            <p className="text-sm mt-2 text-muted">
                                Conducted laboratory sessions and tutorials while pursuing doctoral research
                            </p>
                        </div>
                    </div>
                </section>

                {/* Courses */}
                <section className="mb-16">
                    <h2 className="section-title">Courses Taught</h2>
                    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {courses.map((course, idx) => (
                            <div key={idx} className="flex items-center justify-between p-4 border border-border rounded-lg card-hover">
                                <span className="font-medium text-sm">{course.name}</span>
                                <span className={`tag text-xs ${course.color}`}>{course.level}</span>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Invited Talks */}
                <section>
                    <h2 className="section-title">Invited Talks & Outreach</h2>
                    <div className="space-y-0">
                        {talks.map((talk, idx) => (
                            <div key={idx} className="pub-item">
                                <div className="font-medium">{talk.title}</div>
                                <p className="text-sm text-muted mt-1">
                                    {talk.event} • {talk.venue} • <span style={{ color: '#f59e0b' }}>{talk.date}</span>
                                </p>
                            </div>
                        ))}
                    </div>
                </section>
            </div>
        </div>
    );
}
