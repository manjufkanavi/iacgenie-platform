import React, { useState, useEffect } from 'react';

interface ResendTimerProps {
  initialSeconds?: number;
  onResend: () => Promise<void> | void;
  disabled?: boolean;
}

const ResendTimer: React.FC<ResendTimerProps> = ({
  initialSeconds = 60,
  onResend,
  disabled = false,
}) => {
  const [seconds, setSeconds] = useState(initialSeconds);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setSeconds(initialSeconds);
  }, [initialSeconds]);

  useEffect(() => {
    if (seconds > 0) {
      const interval = setInterval(() => {
        setSeconds((prev) => prev - 1);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [seconds]);

  const handleResend = async () => {
    if (seconds > 0 || isLoading || disabled) return;
    setIsLoading(true);
    try {
      await onResend();
      setSeconds(initialSeconds);
    } catch (err) {
      console.error('Resend failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="text-center" data-testid="resend-timer-container">
      <p className="text-sm text-gray-500">
        Didn't receive the code?{' '}
        <button
          type="button"
          onClick={handleResend}
          disabled={seconds > 0 || isLoading || disabled}
          className={`font-semibold transition-colors focus:outline-none ${
            seconds > 0 || isLoading || disabled
              ? 'text-gray-400 cursor-not-allowed'
              : 'text-brand-primary hover:text-brand-primary/80 hover:underline'
          }`}
          data-testid="resend-timer-button"
        >
          {isLoading ? (
            <span className="inline-block w-4 h-4 border-2 border-brand-primary border-t-transparent rounded-full animate-spin align-middle" />
          ) : seconds > 0 ? (
            `Resend in ${seconds}s`
          ) : (
            'Resend code'
          )}
        </button>
      </p>
    </div>
  );
};

export default ResendTimer;
