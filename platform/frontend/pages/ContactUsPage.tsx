import React, { useState } from 'react';
import Button from '../ui/Button';
import Input from '../ui/Input';
import Textarea from '../ui/Textarea';
import Card from '../ui/Card';
import FormGroup from '../ui/FormGroup';

interface FormData {
    name: string;
    email: string;
    subject: string;
    message: string;
}

const ContactUsPage: React.FC = () => {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [formData, setFormData] = useState<FormData>({
        name: '',
        email: '',
        subject: '',
        message: ''
    });
    const [formStatus, setFormStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

    // SMTP2GO API Configuration
    const SMTP_API_KEY = import.meta.env.VITE_SMTP_API_KEY || 'api-D6548F2A67D64E928B26C119A011C60C';
    const SMTP_API_URL = 'https://api.smtp2go.com/v3/email/send';
    const RECIPIENT_EMAIL = import.meta.env.VITE_SUPPORT_EMAIL || 'manjufkanavi@gmail.com';

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        setFormStatus(null);

        try {
            const response = await fetch(SMTP_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    api_key: SMTP_API_KEY,
                    to: [RECIPIENT_EMAIL],
                    from: formData.email,
                    from_name: formData.name,
                    subject: `[Iacgenie Contact] ${formData.subject}`,
                    html_body: `
                        <div style="font-family: Arial, sans-serif; line-height: 1.6;">
                            <h2 style="color: #333;">New Contact Form Submission</h2>
                            <p><strong>Name:</strong> ${formData.name}</p>
                            <p><strong>Email:</strong> ${formData.email}</p>
                            <p><strong>Subject:</strong> ${formData.subject}</p>
                            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                            <p><strong>Message:</strong></p>
                            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
                                ${formData.message.replace(/\n/g, '<br>')}
                            </div>
                        </div>
                    `,
                }),
            });

            const data = await response.json();

            if (response.ok && data.success) {
                setFormStatus({ type: 'success', message: 'Thank you for your message! We will get back to you shortly.' });
                setFormData({ name: '', email: '', subject: '', message: '' });
            } else {
                setFormStatus({ type: 'error', message: data.message || 'Failed to send message. Please try again.' });
            }
        } catch (error) {
            console.error('Error sending email:', error);
            setFormStatus({ type: 'error', message: 'Network error. Please check your connection and try again.' });
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleInputChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setFormData(prev => ({ ...prev, [field]: e.target.value }));
    };

    return (
        <div className="bg-gray-50 dark:bg-slate-950 py-16 sm:py-24 transition-colors duration-200">
            <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="text-center">
                    <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white sm:text-5xl">Contact Us</h1>
                    <p className="mt-4 text-lg text-gray-600 dark:text-slate-400">
                        Have a question or feedback? We'd love to hear from you.
                    </p>
                </div>

                {formStatus && (
                    <div className={`mt-4 p-4 rounded-lg ${formStatus.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {formStatus.message}
                    </div>
                )}

                <Card className="mt-12">
                    <FormGroup onSubmit={handleSubmit} isSubmitting={isSubmitting}>
                        <Input 
                            id="name" 
                            label="Full Name" 
                            type="text" 
                            autoComplete="name" 
                            required 
                            value={formData.name}
                            onChange={handleInputChange('name')}
                            disabled={isSubmitting}
                        />
                        <Input 
                            id="email" 
                            label="Email Address" 
                            type="email" 
                            autoComplete="email" 
                            required 
                            value={formData.email}
                            onChange={handleInputChange('email')}
                            disabled={isSubmitting}
                        />
                        <Input 
                            id="subject" 
                            label="Subject" 
                            type="text" 
                            required 
                            value={formData.subject}
                            onChange={handleInputChange('subject')}
                            disabled={isSubmitting}
                        />
                        <Textarea 
                            id="message" 
                            label="Message" 
                            rows={4} 
                            required 
                            value={formData.message}
                            onChange={handleInputChange('message')}
                            disabled={isSubmitting}
                        />
                        <div>
                            <Button 
                                type="submit" 
                                size="lg" 
                                className="w-full"
                                isLoading={isSubmitting}
                                disabled={isSubmitting}
                            >
                                {isSubmitting ? 'Sending...' : 'Send Message'}
                            </Button>
                        </div>
                    </FormGroup>
                </Card>
            </div>
        </div>
    );
};

export default ContactUsPage;
