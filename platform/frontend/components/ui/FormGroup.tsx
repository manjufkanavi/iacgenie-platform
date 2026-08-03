import React from 'react';

interface FormGroupProps {
  children: React.ReactNode;
  onSubmit: (e: React.FormEvent) => void;
  className?: string;
  isSubmitting?: boolean;
  disabled?: boolean;
}

const FormGroup: React.FC<FormGroupProps> = ({ 
  children, 
  onSubmit, 
  className = "space-y-6",
  isSubmitting = false,
  disabled = false
}) => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isSubmitting && !disabled) {
      onSubmit(e);
    }
  };

  return (
    <form 
      onSubmit={handleSubmit} 
      className={className}
      noValidate
    >
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          // Disable form elements when form is submitting
          if (isSubmitting || disabled) {
            return React.cloneElement(child, {
              disabled: true,
              'aria-disabled': true
            } as any);
          }
        }
        return child;
      })}
    </form>
  );
};

export default FormGroup; 