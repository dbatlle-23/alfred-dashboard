def corregir_linea_especifica():
    # Leer el archivo
    with open('layouts/smart_locks.py', 'r') as file:
        lines = file.readlines()
    
    # Corregir específicamente la línea 2586
    if len(lines) > 2586:
        # Determinar la indentación correcta
        # Buscar el bloque try anterior
        for i in range(2586, 2570, -1):
            if "try:" in lines[i]:
                # La indentación del except debe coincidir con la del try
                indent_level = len(lines[i]) - len(lines[i].lstrip())
                # Corregir la línea del logger.error con la misma indentación
                content = lines[2586].lstrip()
                lines[2586] = " " * indent_level + content
                break
    
    # Guardar los cambios
    with open('layouts/smart_locks.py.fixed', 'w') as file:
        file.writelines(lines)
    
    print("Corrección específica aplicada. El archivo se ha guardado como 'layouts/smart_locks.py.fixed'")

if __name__ == "__main__":
    corregir_linea_especifica() 