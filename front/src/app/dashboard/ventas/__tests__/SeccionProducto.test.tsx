import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SeccionProducto } from '../SeccionProducto';
import * as apiClient from '@/lib/api-client';

// Mock de api.articulos.buscar
jest.mock('@/lib/api-client');

describe('SeccionProducto - Tests del Scanner', () => {
    const defaultProps = {
        inputRef: { current: null },
        codigo: '',
        setCodigoEscaneado: jest.fn(),
        handleKeyDown: jest.fn(),
        productos: [
            {
                id: '1',
                nombre: 'Producto Test 1',
                precio_venta: 100,
                venta_negocio: 90,
                stock_actual: 10,
                unidad_venta: 'unidad',
            },
            {
                id: '2',
                nombre: 'Producto Test 2',
                precio_venta: 200,
                venta_negocio: 180,
                stock_actual: 5,
                unidad_venta: 'unidad',
            },
        ],
        productoSeleccionado: null,
        setProductoSeleccionado: jest.fn(),
        open: false,
        setOpen: jest.fn(),
        tipoClienteSeleccionadoId: '0',
        popoverOpen: false,
        setPopoverOpen: jest.fn(),
        productoEscaneado: null,
        cantidadEscaneada: 1,
        setCantidadEscaneada: jest.fn(),
        handleAgregarDesdePopover: jest.fn(),
        persistirProducto: false,
        setPersistirProducto: jest.fn(),
        onRefrescarProductos: jest.fn(),
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    // ✅ TEST 1: SCANNER BÁSICO
    describe('Test 1: Scanner básico (código de barras + ENTER)', () => {
        it('Debería llamar handleKeyDown cuando se presiona ENTER con código', async () => {
            const setCodigoEscaneado = jest.fn();
            const handleKeyDown = jest.fn();

            const { rerender } = render(
                React.createElement(SeccionProducto, {
                    ...defaultProps,
                    setCodigoEscaneado,
                    handleKeyDown,
                    codigo: '',
                })
            );

            // Obtener el input
            const input = screen.getByPlaceholderText(
                'Escribe código o nombre (máximo 3-4 coincidencias)'
            );

            // Simular que el scanner escribe el código
            fireEvent.change(input, { target: { value: '123456789' } });
            expect(setCodigoEscaneado).toHaveBeenCalledWith('123456789');

            // Actualizar props con el nuevo código
            rerender(
                React.createElement(SeccionProducto, {
                    ...defaultProps,
                    codigo: '123456789',
                    setCodigoEscaneado,
                    handleKeyDown,
                })
            );

            // Presionar ENTER
            fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

            // Verificar que handleKeyDown fue llamado
            expect(handleKeyDown).toHaveBeenCalled();
        });

        it('No debería hacer nada si presiona ENTER sin código', async () => {
            const handleKeyDown = jest.fn();

            render(
                React.createElement(SeccionProducto, {
                    ...defaultProps,
                    codigo: '',
                    handleKeyDown,
                })
            );

            const input = screen.getByPlaceholderText(
                'Escribe código o nombre (máximo 3-4 coincidencias)'
            );

            // Presionar ENTER sin código
            fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

            // No debería llamar handleKeyDown
            expect(handleKeyDown).not.toHaveBeenCalled();
        });
    });

    // ✅ TEST 2: BÚSQUEDA MANUAL
    describe('Test 2: Búsqueda manual (escribir código y abrir dropdown)', () => {
        beforeEach(() => {
            // Mock del API para búsqueda
            (apiClient.api.articulos.buscar).mockResolvedValue({
                success: true,
                data: [
                    {
                        id: 1,
                        descripcion: 'Producto Test Búsqueda',
                        precio_venta: 150,
                        venta_negocio: 135,
                        stock_actual: 8,
                        unidad_venta: 'unidad',
                    },
                ],
            });
        });

        it('Debería llamar setCodigoEscaneado cuando el usuario escribe', async () => {
            const setCodigoEscaneado = jest.fn();

            render(
                React.createElement(SeccionProducto, {
                    ...defaultProps,
                    setCodigoEscaneado,
                    codigo: '',
                })
            );

            const input = screen.getByPlaceholderText(
                'Escribe código o nombre (máximo 3-4 coincidencias)'
            );

            // Escribir en el input
            fireEvent.change(input, { target: { value: 'Producto' } });

            expect(setCodigoEscaneado).toHaveBeenCalledWith('Producto');
        });
    });

    // ✅ TEST 3: TECLA ESCAPE
    describe('Test 3: Tecla ESCAPE (cerrar dropdown)', () => {
        it('Debería cerrar el dropdown cuando se presiona ESC', async () => {
            const setPopoverOpen = jest.fn();

            render(
                React.createElement(SeccionProducto, {
                    ...defaultProps,
                    popoverOpen: true,
                    setPopoverOpen,
                })
            );

            const input = screen.getByPlaceholderText(
                'Escribe código o nombre (máximo 3-4 coincidencias)'
            );

            // Presionar ESC
            fireEvent.keyDown(input, { key: 'Escape', code: 'Escape' });

            // Verificar que setPopoverOpen fue llamado con false
            expect(setPopoverOpen).toHaveBeenCalledWith(false);
        });
    });

    // ✅ TEST 4: ARROW DOWN (abrir dropdown manualmente)
    describe('Test 4: Arrow Down (mostrar productos)', () => {
        it('Debería abrir el dropdown cuando se presiona Arrow Down', async () => {
            const setPopoverOpen = jest.fn();

            render(
                React.createElement(SeccionProducto, {
                    ...defaultProps,
                    codigo: '',
                    popoverOpen: false,
                    setPopoverOpen,
                    productos: defaultProps.productos,
                })
            );

            const input = screen.getByPlaceholderText(
                'Escribe código o nombre (máximo 3-4 coincidencias)'
            );

            // Presionar Arrow Down
            fireEvent.keyDown(input, { key: 'ArrowDown', code: 'ArrowDown' });

            // Verificar que setPopoverOpen fue llamado con true
            expect(setPopoverOpen).toHaveBeenCalledWith(true);
        });
    });

    // ✅ TEST 5: Cambios en el código
    describe('Test 5: Limpiar selección cuando se modifica el código', () => {
        it('Debería limpiar la selección cuando cambia el código', async () => {
            const setProductoSeleccionado = jest.fn();
            const setCodigoEscaneado = jest.fn();

            const productoSeleccionado = {
                id: '1',
                nombre: 'Laptop XYZ',
                precio_venta: 1000,
                venta_negocio: 900,
                stock_actual: 3,
                unidad_venta: 'unidad',
            };

            render(
                React.createElement(SeccionProducto, {
                    ...defaultProps,
                    codigo: 'Laptop XYZ',
                    setCodigoEscaneado,
                    setProductoSeleccionado,
                    productoSeleccionado,
                })
            );

            const input = screen.getByPlaceholderText(
                'Escribe código o nombre (máximo 3-4 coincidencias)'
            );

            // Cambiar el código
            fireEvent.change(input, { target: { value: 'Producto diferente' } });

            // Debería limpiar la selección anterior
            expect(setProductoSeleccionado).toHaveBeenCalledWith(null);
        });
    });
});

