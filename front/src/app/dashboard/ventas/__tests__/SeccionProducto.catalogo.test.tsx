import type { ComponentProps } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { SeccionProducto } from "../SeccionProducto";
import * as apiClient from "@/lib/api-client";
import {
  limpiarCatalogoVigente,
  publicarCatalogoVigente,
} from "@/lib/offline/catalogo-vigente";

jest.mock("@/lib/api-client");
jest.mock("@/lib/offline/catalogo-search", () => ({
  buscarArticulosLocal: jest.fn().mockResolvedValue([]),
}));

const producto = {
  id: "10",
  nombre: "Yerba",
  precio_venta: 100,
  venta_negocio: 80,
  stock_actual: 3,
  unidad_venta: "unidad",
  precio_manual: false,
};

function renderBuscador(
  extra: Partial<ComponentProps<typeof SeccionProducto>> = {},
) {
  return render(
    <SeccionProducto
      inputRef={{ current: null }}
      codigo="yer"
      setCodigoEscaneado={jest.fn()}
      handleKeyDown={jest.fn()}
      productoSeleccionado={producto}
      setProductoSeleccionado={jest.fn()}
      open={false}
      setOpen={jest.fn()}
      tipoClienteSeleccionadoId="0"
      popoverOpen
      setPopoverOpen={jest.fn()}
      productoEscaneado={null}
      cantidadEscaneada={1}
      setCantidadEscaneada={jest.fn()}
      handleAgregarDesdePopover={jest.fn()}
      persistirProducto={false}
      setPersistirProducto={jest.fn()}
      onRefrescarProductos={jest.fn()}
      offlineHabilitado
      idEmpresa={39}
      catalogoResetTick={1}
      {...extra}
    />,
  );
}

describe("SeccionProducto tras actualizar precios", () => {
  beforeEach(() => {
    limpiarCatalogoVigente();
    jest.mocked(apiClient.api.articulos.buscar).mockResolvedValue({
      success: true,
      data: [
        {
          id: 10,
          descripcion: "Yerba",
          precio_venta: 100,
          venta_negocio: 80,
          stock_actual: 3,
          unidad_venta: "unidad",
          precio_manual: false,
        },
      ],
    });
  });

  it("muestra el precio nuevo del servidor aunque la búsqueda responda el viejo", async () => {
    const setProductoSeleccionado = jest.fn();
    publicarCatalogoVigente(39, [
      { id: "10", precio_venta: 250, venta_negocio: 200, precio_manual: false },
    ]);

    renderBuscador({ setProductoSeleccionado });

    expect(await screen.findByText("$250")).toBeInTheDocument();
    await waitFor(() => {
      expect(setProductoSeleccionado).toHaveBeenCalledWith(
        expect.objectContaining({ id: "10", precio_venta: 250, venta_negocio: 200 }),
      );
    });
  });

  it("no pisa el producto de precio manual seleccionado", async () => {
    const setProductoSeleccionado = jest.fn();
    publicarCatalogoVigente(39, [
      { id: "10", precio_venta: 250, venta_negocio: 200, precio_manual: true },
    ]);

    renderBuscador({
      setProductoSeleccionado,
      productoSeleccionado: { ...producto, precio_manual: true },
    });

    await waitFor(() => {
      expect(apiClient.api.articulos.buscar).toHaveBeenCalled();
    });
    expect(setProductoSeleccionado).not.toHaveBeenCalled();
  });
});
