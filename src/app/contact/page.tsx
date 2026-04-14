import Link from "next/link";
import { Mail, MapPin, Linkedin, Building2, Phone } from "lucide-react";

export default function ContactPage() {
    return (
        <div className="min-h-screen bg-dots-pattern">
            <div className="max-w-5xl mx-auto px-4 md:px-8 py-16">
                <div className="animate-fade-in-up">
                    <h1 className="text-3xl font-bold mb-6">Get in Touch</h1>
                    <p className="text-muted text-lg mb-12">
                        I am always open to discussing research collaborations, student mentorship opportunities,
                        and academic consulting. Please feel free to reach out through any of the channels below.
                    </p>

                    <div className="grid gap-6">
                        {/* Email Card */}
                        <div className="p-6 bg-card border border-border rounded-xl card-hover flex items-start gap-4">
                            <div className="p-3 bg-blue-50 text-primary rounded-lg">
                                <Mail className="h-6 w-6" />
                            </div>
                            <div>
                                <h3 className="font-semibold text-lg mb-1">Email</h3>
                                <p className="text-muted mb-2">For all research and academic inquiries:</p>
                                <Link
                                    href="mailto:rohan.katti@bennett.edu.in"
                                    className="text-primary hover:underline font-medium"
                                >
                                    rohan.katti@bennett.edu.in
                                </Link>
                            </div>
                        </div>

                        {/* LinkedIn Card */}
                        <div className="p-6 bg-card border border-border rounded-xl card-hover flex items-start gap-4">
                            <div className="p-3 bg-blue-50 text-[#0077b5] rounded-lg">
                                <Linkedin className="h-6 w-6" />
                            </div>
                            <div>
                                <h3 className="font-semibold text-lg mb-1">LinkedIn</h3>
                                <p className="text-muted mb-2">Connect with me for professional updates:</p>
                                <Link
                                    href="https://www.linkedin.com/in/rohan-katti-b562699b/"
                                    target="_blank"
                                    className="text-primary hover:underline font-medium"
                                >
                                    View LinkedIn Profile
                                </Link>
                            </div>
                        </div>

                        {/* Office Address Card */}
                        <div className="p-6 bg-card border border-border rounded-xl card-hover flex items-start gap-4">
                            <div className="p-3 bg-blue-50 text-primary rounded-lg">
                                <MapPin className="h-6 w-6" />
                            </div>
                            <div>
                                <h3 className="font-semibold text-lg mb-1">Office Location</h3>
                                <p className="text-muted mb-1">
                                    <strong>Room No:</strong> FX-404
                                </p>
                                <p className="text-muted leading-relaxed">
                                    Department of Electronics & Communication Engineering,<br />
                                    School of Engineering and Applied Sciences,<br />
                                    Bennett University, Plot Nos 8-11,<br />
                                    TechZone 2, Greater Noida,<br />
                                    Uttar Pradesh 201310, India
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
