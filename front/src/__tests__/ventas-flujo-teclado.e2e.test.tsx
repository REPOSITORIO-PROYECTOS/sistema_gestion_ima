/**
 * E2E de flujo de teclado en ventas (componentes reales, sin backend).
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SeccionProducto } from "@/app/dashboard/ventas/SeccionProducto";
import { SeccionCantidad } from "@/app/dashboard/ventas/SeccionCantidad";
import { VENTAS_CAMPOS, focusVentasCampo, TIPO_COMPROBANTE_DEFAULT, tipoComprobanteDesdeFlecha } from "@/lib/ventas-form-flow";

describe("Ventas — flujo teclado E2E", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("Paso 1→2: producto → cantidad", () => {
    it("Enter con producto ya seleccionado avanza al callback de cantidad", () => {
      const onProductoConfirmado = jest.fn();
      const producto = {
        id: "10",
        nombre: "Gaseosa 500ml",
        precio_venta: 1200,
        venta_negocio: 1100,
        stock_actual: 5,
        unidad_venta: "unidad",
      };

      render(
        <SeccionProducto
          inputRef={{ current: null }}
          codigo="Gaseosa 500ml"
          setCodigoEscaneado={jest.fn()}
          handleKeyDown={jest.fn()}
          productoSeleccionado={producto}
          setProductoSeleccionado={jest.fn()}
          open={false}
          setOpen={jest.fn()}
          tipoClienteSeleccionadoId="0"
          popoverOpen={false}
          setPopoverOpen={jest.fn()}
          productoEscaneado={null}
          cantidadEscaneada={1}
          setCantidadEscaneada={jest.fn()}
          handleAgregarDesdePopover={jest.fn()}
          persistirProducto={false}
          setPersistirProducto={jest.fn()}
          onRefrescarProductos={jest.fn()}
          onProductoConfirmado={onProductoConfirmado}
        />,
      );

      const input = screen.getByPlaceholderText("Escribí nombre o escaneá código de barras");
      fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

      expect(onProductoConfirmado).toHaveBeenCalledTimes(1);
    });
  });

  describe("Paso 2→3: cantidad → agregar", () => {
    it("Enter en cantidad dispara onEnterConfirm (agregar producto)", () => {
      const onEnterConfirm = jest.fn();

      render(
        <SeccionCantidad
          cantidadInputRef={{ current: null }}
          modoVenta="unidad"
          cantidadUnidad={2}
          setCantidadUnidad={jest.fn()}
          stockActual={99}
          unidadDeVenta="unidad"
          inputCantidadGranel="1"
          handleCantidadGranelChange={jest.fn()}
          inputPrecioGranel=""
          handlePrecioGranelChange={jest.fn()}
          onEnterConfirm={onEnterConfirm}
        />,
      );

      const cantidad = document.getElementById(VENTAS_CAMPOS.cantidadUnidad);
      expect(cantidad).toBeTruthy();
      fireEvent.keyDown(cantidad!, { key: "Enter", code: "Enter" });

      expect(onEnterConfirm).toHaveBeenCalledTimes(1);
    });

    it("Enter en cantidad granel avanza al campo precio", async () => {
      const precio = document.createElement("input");
      precio.id = VENTAS_CAMPOS.precioGranel;
      document.body.appendChild(precio);
      const focusSpy = jest.spyOn(precio, "focus");

      render(
        <SeccionCantidad
          cantidadInputRef={{ current: null }}
          modoVenta="granel"
          cantidadUnidad={1}
          setCantidadUnidad={jest.fn()}
          stockActual={99}
          unidadDeVenta="kg"
          inputCantidadGranel="0.5"
          handleCantidadGranelChange={jest.fn()}
          inputPrecioGranel="100"
          handlePrecioGranelChange={jest.fn()}
          onEnterConfirm={jest.fn()}
        />,
      );

      const cantidadGranel = document.getElementById(VENTAS_CAMPOS.cantidadGranel);
      fireEvent.keyDown(cantidadGranel!, { key: "Enter", code: "Enter" });

      await waitFor(() => {
        expect(focusSpy).toHaveBeenCalled();
      });
    });
  });

  describe("Utilidad focusVentasCampo", () => {
    it("enfoca el input por id", async () => {
      const input = document.createElement("input");
      input.id = VENTAS_CAMPOS.cantidadUnidad;
      document.body.appendChild(input);
      const focusSpy = jest.spyOn(input, "focus");

      focusVentasCampo(VENTAS_CAMPOS.cantidadUnidad);

      await waitFor(() => {
        expect(focusSpy).toHaveBeenCalled();
      });
    });
  });

  describe("Tipo de comprobante (caja básica)", () => {
    it("predeterminado es comprobante (recibo)", () => {
      expect(TIPO_COMPROBANTE_DEFAULT).toBe("recibo");
    });

    it("flecha izquierda selecciona comprobante", () => {
      expect(tipoComprobanteDesdeFlecha("ArrowLeft")).toBe("recibo");
    });

    it("flecha derecha selecciona factura", () => {
      expect(tipoComprobanteDesdeFlecha("ArrowRight")).toBe("factura");
    });
  });
});
