import React, { useRef, useState } from 'react';
import { Loader2 } from 'lucide-react'; // Importamos un ícono de carga

interface Props {
  onFileSelect: (file: File) => void;
  isLoading: boolean; // <-- 1. Añadimos la prop para el estado de carga
}

const ExcelUploader: React.FC<Props> = ({ onFileSelect, isLoading }) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateAndSend = (file: File) => {
    // Si ya está cargando, no hacemos nada.
    if (isLoading) return;

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
    // Si ya está cargando, no hacemos nada.
    if (isLoading) return;

    const file = e.dataTransfer.files[0];
    validateAndSend(file);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      validateAndSend(file);
    }
  };

  const handleClick = () => {
    // Si ya está cargando, no abrimos el selector de archivos.
    if (isLoading) return;
    inputRef.current?.click();
  }

  // Clases CSS dinámicas para el estado de carga y arrastre
  const containerClasses = `border-2 border-dashed rounded-xl p-6 text-center transition-colors
    ${isLoading 
        ? 'cursor-not-allowed bg-gray-100 border-gray-200' 
        : 'cursor-pointer'
    }
    ${isDragging 
        ? 'border-blue-400 bg-blue-50' 
        : 'border-gray-300 hover:border-gray-400'
    }`;

  return (
    <div
      className={containerClasses}
      onDragOver={(e) => { e.preventDefault(); if (!isLoading) setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      {/* --- 2. Mostramos contenido diferente si está cargando --- */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center text-gray-500">
            <Loader2 className="h-8 w-8 animate-spin mb-2" />
            <p className="text-sm font-semibold">Procesando archivo...</p>
            <p className="text-xs">Esto puede tardar unos segundos.</p>
        </div>
      ) : (
        <>
          <p className="mb-2 text-sm text-gray-600">
            Arrastrá un archivo Excel o hacé clic para subir
          </p>
          {error && <p className="text-red-600 text-sm">{error}</p>}
        </>
      )}

      <input
        type="file"
        accept=".xls,.xlsx"
        className="hidden"
        ref={inputRef}
        onChange={handleChange}
        disabled={isLoading} // Deshabilitamos el input nativo
      />
    </div>
  );
};

export default ExcelUploader;