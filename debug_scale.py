import serial
import serial.tools.list_ports
import time

def list_ports():
    ports = serial.tools.list_ports.comports()
    print("Puertos disponibles:")
    for p in ports:
        print(f"  {p.device} - {p.description}")
    return [p.device for p in ports]

def test_port(port, baudrate):
    print(f"\nProbando puerto {port} a {baudrate} baudios...")
    try:
        with serial.Serial(port, baudrate, timeout=2) as ser:
            print("  Puerto abierto. Esperando datos (5 segundos)...")
            
            # Try to clear buffer
            ser.reset_input_buffer()
            
            # Read for 5 seconds
            start = time.time()
            data_received = False
            while time.time() - start < 5:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    print(f"  [RECIBIDO] Hex: {data.hex()} | ASCII: {data}")
                    data_received = True
                time.sleep(0.1)
            
            if not data_received:
                print("  No se recibieron datos.")
                # Try sending a trigger
                print("  Intentando enviar triggers (P, W, ENQ)...")
                for trigger in [b'P', b'W', b'\x05', b'\r\n']:
                    ser.write(trigger)
                    time.sleep(0.5)
                    if ser.in_waiting > 0:
                         data = ser.read(ser.in_waiting)
                         print(f"  [RESPUESTA a {trigger}] Hex: {data.hex()} | ASCII: {data}")
                         data_received = True
            
            return data_received

    except serial.SerialException as e:
        print(f"  Error abriendo puerto: {e}")
        return False

def main():
    available_ports = list_ports()
    if not available_ports:
        print("No se encontraron puertos COM.")
        return

    target_port = input(f"\nIngrese el puerto a probar (ej: {available_ports[0]}): ").strip()
    if not target_port:
        target_port = available_ports[0]
    
    baudrates = [9600, 2400, 4800, 19200]
    
    print(f"\nIniciando diagnóstico en {target_port}...")
    
    for baud in baudrates:
        if test_port(target_port, baud):
            print(f"\n¡ÉXITO! Se recibieron datos en {target_port} a {baud} baudios.")
            break
    else:
        print("\nDiagnóstico finalizado. No se pudo establecer comunicación clara.")

if __name__ == "__main__":
    main()
