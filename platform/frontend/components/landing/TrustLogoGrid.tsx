import React from 'react';

interface TrustLogo {
  name: string;
  icon?: React.ReactNode;
  alt: string;
}

interface TrustLogoGridProps {
  logos?: TrustLogo[];
}

const TrustLogoGrid: React.FC<TrustLogoGridProps> = ({ logos }) => {
  const defaultLogos: TrustLogo[] = [
    { name: 'AWS', alt: 'Amazon Web Services', icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="18" viewBox="0 0 18 18">
        <path fill="#FF9900" d="M0 0h18v18H0z"/>
        <path fill="#232F3E" d="M5.19 14.34h1.75l-.22-1.12h-1.3zM12.8 14.34h1.75l-.22-1.12h-1.3z"/>
        <path fill="#FFFFFF" d="M6.08 6.57c0-.98.7-1.7 1.8-1.7 1.12 0 1.8.72 1.8 1.7v.52h-1.58v-.47c0-.28-.2-.43-.52-.43-.3 0-.5.15-.5.43v2.85c0 .28.2.43.5.43.32 0 .52-.15.52-.43v-.48h1.58v.52c0 .98-.7 1.7-1.8 1.7-1.1 0-1.8-.72-1.8-1.7V6.57zm4.12 4.4a2.2 2.2 0 0 1-1.83 1.03c-1.3 0-2.22-.8-2.22-2.28 0-1.47.92-2.27 2.22-2.27a2.2 2.2 0 0 1 1.83 1.02l-1.3.73c-.15-.3-.3-.42-.6-.42-.52 0-.77.38-.77 1 0 .6.25.98.78.98.3 0 .45-.12.58-.42l1.3.71zm3.8-4.48c-1.33 0-2.2.83-2.2 2.28 0 1.45.87 2.28 2.2 2.28 1.33 0 2.2-.83 2.2-2.28 0-1.45-.87-2.28-2.2-2.28zm0 3.5c-.55 0-.8-.4-.8-1.18 0-.78.25-1.18.8-1.18.55 0 .8.4.8 1.18 0 .78-.25 1.18-.8 1.18z"/>
      </svg>
    )},
    { name: 'GCP', alt: 'Google Cloud Platform', icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="24" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M12.0001 14.4884L12 14.4885C8.86876 14.4884 6.25562 12.0913 6.25562 9.2064C6.25562 6.32149 8.86876 3.92444 12 3.92444C13.8441 3.92444 15.4346 4.81438 16.3986 6.13116L14.1542 7.9157C13.6828 7.31885 12.9157 6.94632 12 6.94632C10.2243 6.94632 8.78309 8.27214 8.78309 9.8703C8.78309 11.4685 10.2243 12.7943 12 12.7943C13.0645 12.7943 13.8829 12.449 14.4286 11.9688L16.6143 13.6946C15.493 14.2323 13.9116 14.4884 12.0001 14.4884Z"/>
        <path fill="#34A853" d="M12 20.0755C10.1559 20.0755 8.56543 19.1856 7.60144 17.8688L9.84581 16.0842C10.3172 16.6811 11.0843 17.0536 12 17.0536C12.7093 17.0536 13.298 16.8288 13.7107 16.4832C14.3314 15.9727 14.5458 15.1963 14.6343 14.342H12V11.6963H17.8059C17.9216 12.4455 18 13.2505 18 14.1331C18 17.5028 15.399 20.0755 12 20.0755Z"/>
        <path fill="#FBBC05" d="M5.42438 12C5.17822 11.2372 5.17822 10.7628 5.42438 10L3.13867 8.16C2.26289 9.80273 2.26289 12.1973 3.13867 13.84L5.42438 12Z"/>
        <path fill="#EA4335" d="M12 6.94632C12.9157 6.94632 13.6828 7.31885 14.1542 7.9157L16.3986 6.13116C15.4346 4.81438 13.8441 3.92444 12 3.92444C9.02576 3.92444 6.54144 5.92871 5.42438 8.16L7.60144 10C8.56543 7.96277 10.1559 6.94632 12 6.94632Z"/>
      </svg>
    )},
    { name: 'Azure', alt: 'Microsoft Azure', icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="24" viewBox="0 0 24 24">
        <path fill="#0078D4" d="M5.85 8.32L11.45 20.25L14.73 9.49L10.36 8.32H5.85ZM12.16 3.75L5.15 20.25H4.25L17.75 3.75H12.16Z"/>
      </svg>
    )},
    { name: 'Kubernetes', alt: 'Kubernetes', icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24">
        <path fill="#306988" d="M17.5 12.5l-1-3h4l-1 3h-1zm-7 0l-1-3h4l-1 3h-1zM5.5 2L3 7h4L9 2H5.5zm13 0l-2.5 5h4l2.5-5H18.5zM5.5 22l2.5-5h-4L3 22h2.5zm13 0l-2.5-5h4L21 22h-2.5zM3 12l2 8h14l2-8H3zm7.5 3.5l1.5 3 1.5-3H10.5z"/>
      </svg>
    )},
    { name: 'Docker', alt: 'Docker', icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24">
        <path fill="#0DB7ED" d="M13.5 4.02c.6-.8 1.7-1.2 3-1.2C19.5 2.82 21 4.02 21 6c0 .3-.1.5-.1.8h-1.4c-.1-.6-.5-1-1-1-.7 0-1.2.4-1.3 1H8.5c-.6 0-1.2.4-1.3 1H3.5c-.1-.3-.1-.5-.1-.8C3.4 4.02 4.9 2.82 6.5 2.8c1.3 0 2.4.4 3 1.2h4zm-5 6c0-.55.45-1 1-1h8c.55 0 1 .45 1 1s-.45 1-1 1h-8c-.55 0-1-.45-1-1zm9.5-3c0 .55-.45 1-1 1h-7c-.55 0-1-.45-1-1s.45-1 1-1h7c.55 0 1 .45 1 1zM6 9.02c-.6 0-1.1.45-1.1 1s.5 1 1.1 1h12c.6 0 1.1-.45 1.1-1s-.5-1-1.1-1H6zm0 3c-.6 0-1.1.45-1.1 1s.5 1 1.1 1h12c.6 0 1.1-.45 1.1-1s-.5-1-1.1-1H6zm0 3c-.6 0-1.1.45-1.1 1s.5 1 1.1 1h7c.6 0 1.1-.45 1.1-1s-.5-1-1.1-1H6zm0 3c-.6 0-1.1.45-1.1 1s.5 1 1.1 1h3c.6 0 1.1-.45 1.1-1s-.5-1-1.1-1H6z"/>
      </svg>
    )},
  ];

  const displayLogos = logos || defaultLogos;

  return (
    <div className="bg-gray-50 py-12 border-y border-gray-200">
      <div className="flex flex-wrap justify-center items-center gap-8 md:gap-16 max-w-6xl mx-auto px-4">
        {displayLogos.map((logo, index) => (
          <div 
            key={index}
            className="h-12 w-auto opacity-60 hover:opacity-100 transition-all duration-200 grayscale hover:grayscale-0 filter hover:scale-105 transform"
            title={logo.alt}
          >
            {logo.icon}
          </div>
        ))}
      </div>
    </div>
  );
};

export default TrustLogoGrid;