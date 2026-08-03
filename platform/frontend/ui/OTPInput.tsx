import React, { useRef, useEffect } from 'react';

interface OTPInputProps {
  value: string[];
  onChange: (value: string[]) => void;
  length?: number;
  disabled?: boolean;
  error?: boolean;
}

const OTPInput: React.FC<OTPInputProps> = ({
  value,
  onChange,
  length = 6,
  disabled = false,
  error = false,
}) => {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, []);

  const handleChange = (index: number, val: string) => {
    if (!/^\d*$/.test(val)) return; // Allow only digits

    const newValue = [...value];
    
    if (val.length > 1) {
      // Handle paste/multi-character entry
      const pastedDigits = val.slice(0, length - index).split('');
      pastedDigits.forEach((digit, i) => {
        if (index + i < length) {
          newValue[index + i] = digit;
        }
      });
      onChange(newValue);
      
      const nextIndex = Math.min(index + pastedDigits.length, length - 1);
      inputRefs.current[nextIndex]?.focus();
    } else {
      newValue[index] = val;
      onChange(newValue);
      
      // Auto-focus next cell
      if (val && index < length - 1) {
        inputRefs.current[index + 1]?.focus();
      }
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      if (!value[index] && index > 0) {
        // Backspace on empty input: clear and focus previous
        const newValue = [...value];
        newValue[index - 1] = '';
        onChange(newValue);
        inputRefs.current[index - 1]?.focus();
      } else if (value[index]) {
        // Clear current input
        const newValue = [...value];
        newValue[index] = '';
        onChange(newValue);
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>, startIndex: number) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').trim();
    if (!/^\d+$/.test(pastedData)) return; // Allow only digits

    const newValue = [...value];
    let pastedCount = 0;

    for (let i = startIndex; i < length && pastedCount < pastedData.length; i++) {
      newValue[i] = pastedData[pastedCount];
      pastedCount++;
    }

    onChange(newValue);

    const targetFocusIndex = Math.min(startIndex + pastedCount, length - 1);
    inputRefs.current[targetFocusIndex]?.focus();
  };

  return (
    <div className="flex justify-center gap-2 sm:gap-3" data-testid="otp-input-container">
      {Array.from({ length }).map((_, index) => (
        <input
          key={index}
          ref={(el) => {
            inputRefs.current[index] = el;
          }}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={length - index} // Allow longer input for paste operations
          value={value[index] || ''}
          disabled={disabled}
          onChange={(e) => handleChange(index, e.target.value)}
          onKeyDown={(e) => handleKeyDown(index, e)}
          onPaste={(e) => handlePaste(e, index)}
          className={`w-12 h-14 sm:w-14 sm:h-16 border-2 rounded-xl text-center text-xl font-bold shadow-sm focus:outline-none focus:ring-4 transition-all duration-250 bg-white ${
            error
              ? 'border-red-300 text-red-600 focus:border-red-500 focus:ring-red-100'
              : 'border-gray-200 text-gray-900 focus:border-brand-primary focus:ring-brand-primary/10'
          } ${disabled ? 'bg-gray-50 text-gray-400 cursor-not-allowed' : ''}`}
          placeholder="-"
          data-testid={`otp-cell-${index}`}
        />
      ))}
    </div>
  );
};

export default OTPInput;
