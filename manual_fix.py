#!/usr/bin/env python3
"""
Script to manually fix specific syntax errors in the smart_locks.py file.
"""

def fix_try_except_block():
    file_path = 'layouts/smart_locks.py'
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Create a backup just in case
    backup_path = file_path + '.manual_fix.bak'
    with open(backup_path, 'w', encoding='utf-8') as backup_file:
        backup_file.writelines(lines)
    
    print(f"Created backup at {backup_path}")
    
    # Find and replace the problematic try/except block
    try_start_line = None
    try_end_line = None
    
    # Look for the problematic section
    for i, line in enumerate(lines):
        if "# PASO 1: Obtener información NFC desde la API para todos los assets" in line:
            # Look for the try block nearby
            for j in range(i, min(i+10, len(lines))):
                if "try:" in lines[j]:
                    try_start_line = j
                    break
            
            if try_start_line:
                # Find closing bracket of ThreadPoolExecutor
                for j in range(try_start_line, len(lines)):
                    if "]" in lines[j] and "futures" in lines[j]:
                        try_end_line = j + 1
                        break
            
            break
    
    if try_start_line and try_end_line:
        # Read the indentation level
        indentation = lines[try_start_line].split("try:")[0]
        
        # Create the fixed code block
        fixed_block = lines[try_start_line:try_end_line]
        # Add proper except clause
        fixed_block.append(indentation + "except Exception as e:\n")
        fixed_block.append(indentation + "    errors.append(str(e))\n")
        fixed_block.append(indentation + "    logger.error(f\"Error al crear ThreadPoolExecutor: {str(e)}\")\n")
        
        # Replace the original lines
        lines[try_start_line:try_end_line] = fixed_block
        
        # Write back to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)
        
        print(f"Fixed try/except block in {file_path}")
    else:
        print("Could not locate the problematic try/except block.")

if __name__ == "__main__":
    fix_try_except_block() 