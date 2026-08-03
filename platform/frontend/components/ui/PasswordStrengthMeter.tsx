import React from 'react';

interface PasswordStrengthMeterProps {
  password: string;
}

const PasswordStrengthMeter: React.FC<PasswordStrengthMeterProps> = ({ password }) => {
  const calculateStrength = (pwd: string) => {
    let score = 0;
    if (!pwd) return score;

    // Length check
    if (pwd.length >= 8) score += 1;
    // Lowercase & Uppercase check
    if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) score += 1;
    // Number check
    if (/\d/.test(pwd)) score += 1;
    // Special character check
    if (/[^A-Za-z0-9]/.test(pwd)) score += 1;

    return score;
  };

  const score = calculateStrength(password);

  const getStrengthConfig = (s: number) => {
    if (!password) return { label: 'Required', color: 'bg-gray-200', text: 'text-gray-400', width: 'w-0' };
    switch (s) {
      case 1:
        return { label: 'Weak', color: 'bg-red-500', text: 'text-red-500', width: 'w-1/4' };
      case 2:
        return { label: 'Fair', color: 'bg-yellow-500', text: 'text-yellow-600', width: 'w-2/4' };
      case 3:
        return { label: 'Good', color: 'bg-yellow-500', text: 'text-yellow-600', width: 'w-3/4' };
      case 4:
        return { label: 'Strong', color: 'bg-green-500', text: 'text-green-600', width: 'w-full' };
      default:
        return { label: 'Very Weak', color: 'bg-red-400', text: 'text-red-400', width: 'w-1/12' };
    }
  };

  const config = getStrengthConfig(score);

  const requirements = [
    { label: 'At least 8 characters', met: password.length >= 8 },
    { label: 'Uppercase & lowercase letters', met: /[a-z]/.test(password) && /[A-Z]/.test(password) },
    { label: 'At least one number', met: /\d/.test(password) },
    { label: 'At least one special character', met: /[^A-Za-z0-9]/.test(password) },
  ];

  return (
    <div className="space-y-2 mt-2" data-testid="password-strength-meter">
      <div className="flex justify-between items-center text-xs font-bold uppercase tracking-wider">
        <span className="text-gray-400">Password Strength</span>
        <span className={config.text} data-testid="password-strength-label">{config.label}</span>
      </div>
      <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 rounded-full ${config.color} ${config.width}`}
          data-testid="password-strength-bar"
        />
      </div>
      
      {/* Requirements List */}
      <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1" data-testid="password-requirements">
        {requirements.map((req, i) => (
          <li key={i} className="flex items-center text-xs space-x-1.5">
            <span
              className={`flex-shrink-0 w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] font-bold ${
                req.met
                  ? 'bg-green-50 text-green-600 border border-green-200'
                  : 'bg-gray-50 text-gray-400 border border-gray-200'
              }`}
            >
              {req.met ? '✓' : '○'}
            </span>
            <span className={req.met ? 'text-gray-600' : 'text-gray-400'}>{req.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default PasswordStrengthMeter;
