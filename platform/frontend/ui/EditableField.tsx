import React from 'react';
import Input from './Input';
import Textarea from './Textarea';

interface EditableFieldProps {
  label: string;
  value: string;
  isEditing: boolean;
  onChange: (value: string) => void;
  type?: 'text' | 'textarea';
  textareaRows?: number;
  placeholder?: string;
  required?: boolean;
  className?: string;
  id?: string;
}

const EditableField: React.FC<EditableFieldProps> = ({
  label,
  value,
  isEditing,
  onChange,
  type = 'text',
  textareaRows = 3,
  placeholder,
  required = false,
  className = '',
  id
}) => {
  if (isEditing) {
    if (type === 'textarea') {
      return (
        <div className={`transform transition-all duration-300 ease-in-out ${className}`}>
          <Textarea
            id={id || `editable-${label.toLowerCase().replace(/\s+/g, '-')}`}
            label={label}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            rows={textareaRows}
            placeholder={placeholder}
            required={required}
            className="transition-all duration-200 ease-in-out focus:ring-2 focus:ring-brand-primary focus:border-brand-primary"
          />
        </div>
      );
    }
    
    return (
      <div className={`transform transition-all duration-300 ease-in-out ${className}`}>
        <Input
          id={id || `editable-${label.toLowerCase().replace(/\s+/g, '-')}`}
          label={label}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          required={required}
          className="transition-all duration-200 ease-in-out focus:ring-2 focus:ring-brand-primary focus:border-brand-primary"
        />
      </div>
    );
  }

  return (
    <div className={`transform transition-all duration-300 ease-in-out ${className}`}>
      <p className="block text-sm font-medium text-gray-700 mb-1">{label}</p>
      <div className="text-sm text-gray-900 bg-gray-50 px-3 py-2 rounded-md border border-gray-200 hover:bg-gray-100 transition-colors duration-200">
        {value || <span className="text-gray-400 italic">No {label.toLowerCase()} set</span>}
      </div>
    </div>
  );
};

export default EditableField; 