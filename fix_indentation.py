#!/usr/bin/env python3
"""
Script to fix indentation issues in the smart_locks.py file.
This script focuses on correcting the most critical indentation errors.
"""

import re
import os

def fix_indentation_issues():
    # Path to the file
    file_path = 'layouts/smart_locks.py'
    
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Make a backup of the original file
    backup_path = file_path + '.bak'
    with open(backup_path, 'w', encoding='utf-8') as backup_file:
        backup_file.writelines(lines)
    
    print(f"Created backup at {backup_path}")
    
    # Fix specific issues based on line numbers from linter errors
    fixed_lines = lines.copy()
    
    # Fix issue 1: Line 1830-1834: Expected indented block
    # This is already fixed based on the grep output above
    
    # Fix issue 2: Lines around 2127-2153: Unexpected indentation and missing except/finally clauses
    for i in range(2120, 2155):
        if i < len(fixed_lines) and re.search(r'^\s*errors = \[\]', fixed_lines[i]):
            # This line should be indented at the same level as the next line (results = [])
            indentation = re.match(r'^(\s*)', fixed_lines[i+1]).group(1)
            fixed_lines[i] = indentation + fixed_lines[i].lstrip()
    
    # Fix the try/except block
    for i in range(2130, 2155):
        if i < len(fixed_lines) and "try:" in fixed_lines[i]:
            try_line_indent = re.match(r'^(\s*)', fixed_lines[i]).group(1)
            except_needed = True
            
            # Look for an existing except clause
            for j in range(i+1, min(i+25, len(fixed_lines))):
                if "except Exception as e:" in fixed_lines[j]:
                    except_needed = False
                    break
            
            # If no except clause found, add one
            if except_needed:
                for j in range(i+1, min(i+25, len(fixed_lines))):
                    if "with concurrent.futures" in fixed_lines[j]:
                        # Add the except clause right after the with block
                        for k in range(j+1, min(j+15, len(fixed_lines))):
                            if fixed_lines[k].strip().endswith("]"):
                                # Insert the except clause after this line
                                fixed_lines.insert(k+1, try_line_indent + "except Exception as e:\n")
                                fixed_lines.insert(k+2, try_line_indent + "    errors.append(str(e))\n")
                                fixed_lines.insert(k+3, try_line_indent + "    logger.error(f\"Error al crear ThreadPoolExecutor: {str(e)}\")\n")
                                break
    
    # Fix the indentation of the next sections (sensor ID issues)
    for i in range(2180, 2320):
        if i < len(fixed_lines) and "cell_id = f\"sensor_{sensor_id}\"" in fixed_lines[i]:
            # Fix indentation of this line and following lines
            correct_indent = re.match(r'^(\s*)', fixed_lines[i-1]).group(1)
            fixed_lines[i] = correct_indent + fixed_lines[i].lstrip()
            
            # Look ahead to fix the next few lines as well
            for j in range(i+1, min(i+10, len(fixed_lines))):
                if fixed_lines[j].strip() and not fixed_lines[j].strip().startswith("#"):
                    fixed_lines[j] = correct_indent + fixed_lines[j].lstrip()
    
    # Write the fixed content back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(fixed_lines)
    
    print(f"Fixed indentation issues in {file_path}")

if __name__ == "__main__":
    fix_indentation_issues() 