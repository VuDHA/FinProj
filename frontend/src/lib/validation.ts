type FieldValidator = (value: string) => string | null;

interface FormField {
  value: string;
  validators?: FieldValidator[];
}

export function required(message = "Trường này là bắt buộc"): FieldValidator {
  return (value) => (value.trim() === "" ? message : null);
}

export function positiveNumber(message = "Phải là số dương"): FieldValidator {
  return (value) => {
    const num = Number(value);
    if (value === "" || Number.isNaN(num) || num <= 0) return message;
    return null;
  };
}

export function nonNegativeNumber(message = "Không được là số âm"): FieldValidator {
  return (value) => {
    const num = Number(value);
    if (value === "" || Number.isNaN(num) || num < 0) return message;
    return null;
  };
}

export function notFutureDate(message = "Không được chọn ngày trong tương lai"): FieldValidator {
  return (value) => {
    if (!value) return null;
    const selected = new Date(value);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (selected > today) return message;
    return null;
  };
}

export function validateForm(fields: Record<string, FormField>): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const [name, field] of Object.entries(fields)) {
    if (!field.validators) continue;
    for (const validator of field.validators) {
      const error = validator(field.value);
      if (error) {
        errors[name] = error;
        break;
      }
    }
  }
  return errors;
}

export function hasErrors(errors: Record<string, string>): boolean {
  return Object.keys(errors).length > 0;
}
