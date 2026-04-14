import Image from "next/image";
import Link from "next/link";
import { ArrowRight, Mail, MapPin, Building2 } from "lucide-react";

export default function Home() {
    return (
        <div className="page-bg-home min-h-screen">
            <div className="max-w-7xl mx-auto px-4 md:px-8 lg:px-12 py-16">
                {/* Hero Section */}
                <section className="grid md:grid-cols-3 gap-12 items-center mb-20 animate-fade-in-up">
                    <div className="md:col-span-1 flex justify-center md:justify-start">
                        <Image
                            src="/profile.jpg"
                            alt="Dr. Rohan Katti"
                            width={280}
                            height={280}
                            className="profile-image"
                            priority
                        />
                    </div>

                    <div className="md:col-span-2">
                        <h1 className="text-4xl font-bold mb-2">Dr. Rohan Katti</h1>
                        <p className="text-xl text-muted mb-4">Assistant Professor</p>

                        <div className="flex flex-wrap items-center gap-4 text-sm text-muted mb-6">
                            <span className="flex items-center gap-1.5">
                                <Building2 className="h-4 w-4" />
                                Department of ECE
                            </span>
                            <span className="flex items-center gap-1.5">
                                <MapPin className="h-4 w-4" />
                                Bennett University
                            </span>
                        </div>

                        <p className="text-lg leading-relaxed mb-6">
                            I am a faculty member at Bennett University specialising in
                            <strong className="text-primary"> Microwave Photonics</strong>,
                            <strong className="text-purple-600"> Silicon Photonics</strong>, and
                            <strong className="text-teal-600"> Photonic Integrated Circuits</strong>. My research centres on developing
                            advanced photonic systems that enable next-generation wireless communication and
                            high-speed signal processing technologies.
                        </p>

                        <div className="flex flex-col sm:flex-row flex-wrap gap-3">
                            <Link
                                href="mailto:rohan.katti@bennett.edu.in"
                                className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-all hover-lift"
                            >
                                <Mail className="h-4 w-4" />
                                Get in Touch
                            </Link>
                            <Link
                                href="/publications"
                                className="inline-flex items-center gap-2 px-5 py-2.5 border border-border text-sm font-medium rounded-lg hover:bg-white transition-all hover-lift"
                            >
                                View Publications
                                <ArrowRight className="h-4 w-4" />
                            </Link>
                        </div>
                    </div>
                </section>

                {/* Research Impact */}
                <section className="mb-20">
                    <h2 className="section-title">Research Impact</h2>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-0 border border-border rounded-xl overflow-hidden">
                        <div className="stat-card border-r border-border card-hover">
                            <div className="stat-number">147</div>
                            <div className="stat-label">Citations</div>
                        </div>
                        <div className="stat-card border-r border-border card-hover">
                            <div className="stat-number" style={{ color: '#8b5cf6' }}>7</div>
                            <div className="stat-label">h-index</div>
                        </div>
                        <div className="stat-card border-r border-border card-hover">
                            <div className="stat-number" style={{ color: '#14b8a6' }}>13</div>
                            <div className="stat-label">Journal Articles</div>
                        </div>
                        <div className="stat-card border-r border-border card-hover">
                            <div className="stat-number" style={{ color: '#f59e0b' }}>10</div>
                            <div className="stat-label">Conference Papers</div>
                        </div>
                        <div className="stat-card card-hover">
                            <div className="stat-number" style={{ color: '#ec4899' }}>1</div>
                            <div className="stat-label">Patent Granted</div>
                        </div>
                    </div>
                </section>

                {/* Research Interests */}
                <section className="mb-20">
                    <h2 className="section-title">Research Interests</h2>
                    <div className="flex flex-wrap gap-2">
                        <span className="tag tag-primary">Optical Communications</span>
                        <span className="tag tag-purple">Microwave Photonics</span>
                        <span className="tag tag-teal">Silicon Photonics</span>
                        <span className="tag tag-amber">Photonic Integrated Circuits</span>
                        <span className="tag tag-rose">All-Optical Computing</span>
                        <span className="tag tag-primary">5G/6G Technologies</span>
                    </div>
                </section>

                {/* Recent Highlights */}
                <section className="mb-20">
                    <h2 className="section-title">Recent Highlights</h2>
                    <div className="space-y-4">
                        <div className="flex gap-4 p-4 rounded-lg bg-card border border-border card-hover accent-blue">
                            <span className="text-sm text-primary font-medium whitespace-nowrap">Sep 2025</span>
                            <p><strong>Excellence in Teaching Award</strong>, Recognised for outstanding contributions to pedagogy at the School of Engineering, Bennett University.</p>
                        </div>
                        <div className="flex gap-4 p-4 rounded-lg bg-card border border-border card-hover accent-purple">
                            <span className="text-sm font-medium whitespace-nowrap" style={{ color: '#8b5cf6' }}>Mar 2024</span>
                            <p><strong>Student Achievement</strong>, Mentored students secured 3rd position at the All India STMicroelectronics Innovation Fair.</p>
                        </div>
                        <div className="flex gap-4 p-4 rounded-lg bg-card border border-border card-hover accent-teal">
                            <span className="text-sm font-medium whitespace-nowrap" style={{ color: '#14b8a6' }}>Feb 2024</span>
                            <p><strong>Research Grant</strong>, Awarded a SEED grant of ₹10 Lakhs for investigating MZI-based modulators.</p>
                        </div>
                        <div className="flex gap-4 p-4 rounded-lg bg-card border border-border card-hover accent-amber">
                            <span className="text-sm font-medium whitespace-nowrap" style={{ color: '#f59e0b' }}>Dec 2023</span>
                            <p><strong>Best Paper Award</strong>, Recognised in the Quantum Photonics track at IEEE WRAP 2023.</p>
                        </div>
                    </div>
                </section>

                {/* Education */}
                <section>
                    <h2 className="section-title">Education</h2>
                    <div className="space-y-0">
                        <div className="timeline-item">
                            <div className="font-semibold">Ph.D. in Microwave Photonics</div>
                            <div className="text-muted text-sm">SRM Institute of Science and Technology, Chennai, 2015-2020</div>
                            <div className="text-sm mt-1">Visvesvaraya PhD Fellowship, MeitY, Govt. of India</div>
                        </div>
                        <div className="timeline-item">
                            <div className="font-semibold">M.Tech. in Communication Systems</div>
                            <div className="text-muted text-sm">SRM Institute of Science and Technology, Chennai, 2013-2015</div>
                            <div className="text-sm mt-1">CGPA: 9.5, Gold Medallist</div>
                        </div>
                        <div className="timeline-item">
                            <div className="font-semibold">B.Tech. in Electronics & Communication Engineering</div>
                            <div className="text-muted text-sm">JNTUH, Hyderabad, 2009-2013</div>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
}
