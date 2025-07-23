import React, { useRef, useState } from 'react';

interface Props {
  onFileSelect: (file: File) => void;
}

const ExcelUploader: React.FC<Props> = ({ onFileSelect }) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateAndSend = (file: File) => {
    if (!file || !file.name.match(/\.(xls|xlsx)$/i)) {
      setError('El archivo debe ser un .xls o .xlsx');
      return;
    }
    setError(null);
    onFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    validateAndSend(file);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      validateAndSend(file);
    }
  };

  return (
    <div
      className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer ${
        isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300'
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <p className="mb-2 text-sm text-gray-600">
        Arrastrá un archivo Excel o hacé clic para subir
      </p>
      {error && <p className="text-red-600 text-sm">{error}</p>}
      <input
        type="file"
        accept=".xls,.xlsx"
        className="hidden"
        ref={inputRef}
        onChange={handleChange}
      />
    </div>
  );
};

export default ExcelUploader;