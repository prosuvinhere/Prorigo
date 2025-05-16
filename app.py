import streamlit as st
import pandas as pd
import tempfile
from tabula import read_pdf
import fitz  # PyMuPDF
import os
import json
import io
from PIL import Image

def convert_tables_to_json(tables):
    """Convert multiple tables into single SurveyJS JSON format"""
    all_elements = []
    for idx, table in enumerate(tables):
        # Create column definitions - removed extra columns
        columns = [
            {"name": col, "title": col, "cellType": "text"}
            for col in table.columns
        ]
        
        # Process rows - removed extra columns
        row_data = {}
        rows = []
        for i in range(len(table)):
            row_name = f"Row {i + 1}"
            rows.append(row_name)
            row_data[row_name] = {
                col: str(table.iloc[i][col]) if pd.notna(table.iloc[i][col]) else ""
                for col in table.columns
            }
        
        # Create element for this table
        element = {
            "type": "matrixdropdown",
            "name": f"Table {idx + 1}",
            "defaultValue": row_data,
            "columns": columns,
            "rows": rows
        }
        all_elements.append(element)
    
    # Combine all elements into final JSON structure
    return {
        "pages": [
            {
                "name": "page1",
                "elements": all_elements
            }
        ]
    }

# Streamlit UI
st.title("PDF Table Extractor & JSON Converter")

# Upload PDF
uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        temp_file_path = temp_file.name

    # Preview PDF as images using PyMuPDF
    st.subheader("PDF Preview")
    try:
        # Open the PDF
        pdf_document = fitz.open(temp_file_path)
        
        # Convert pages to images
        for page_num in range(len(pdf_document)):
            # Render page to an image
            page = pdf_document[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # High resolution
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Display the image
            st.image(img, caption=f"Page {page_num+1}", use_container_width=True)
        
        # Close the PDF document
        pdf_document.close()
    
    except Exception as preview_error:
        st.error(f"Error previewing PDF: {preview_error}")
    
    # Extract tables
    try:
        tables = read_pdf(temp_file_path, pages='all', multiple_tables=True, pandas_options={'header': 0})
        if tables:
            df = tables[0]  # Use the first table
            
            # Replace NaN values with empty strings
            df = df.fillna("")
            
            # Trim rows slider
            st.write("Trim rows from top and bottom:")
            trim_range = st.slider(
                "Select range of rows to keep:",
                0, len(df)-1, (0, len(df)-1),
                key="trim_slider"
            )
            
            # Apply trimming
            trimmed_df = df.iloc[trim_range[0]:trim_range[1]+1]
            
            st.subheader("Trimmed Table")
            edited_df = st.data_editor(trimmed_df)  # Allow editing of the table
            
            # Split table - initial value set to 1
            num_splits = st.number_input("Enter number of parts to split the table into:", 
                                       min_value=1, 
                                       max_value=len(edited_df), 
                                       value=1)  # Changed initial value to 1
            
            split_points = [st.number_input(f"Enter row index for split {i+1}:", 
                                          min_value=0, 
                                          max_value=len(edited_df)-1, 
                                          value=int(i * len(edited_df) / num_splits)) 
                          for i in range(1, num_splits)]
            split_points = [0] + split_points + [len(edited_df)]
            
            split_tables = [edited_df.iloc[split_points[i]:split_points[i+1]] 
                          for i in range(len(split_points)-1)]
            
            # Display split tables
            for idx, new_table in enumerate(split_tables):
                st.subheader(f"Split Table {idx+1}")
                st.dataframe(new_table)
                
                # Download CSV option
                csv = new_table.to_csv(index=False)
                st.download_button(
                    f"Download Split Table {idx+1} (CSV)", 
                    csv, 
                    f"split_table_{idx+1}.csv", 
                    "text/csv"
                )
            
            # Convert all split tables to single JSON
            combined_json = convert_tables_to_json(split_tables)
            
            # Display and download JSON
            st.subheader("Combined JSON Output")
            st.markdown("[Test your JSON in SurveyJS Creator](https://surveyjs.io/create-free-survey)")
            st.json(combined_json)
            
            # Download JSON option
            json_str = json.dumps(combined_json, indent=2)
            st.download_button(
                "Download Combined JSON",
                json_str,
                "combined_tables.json",
                "application/json"
            )
        else:
            st.warning("No tables found in the PDF.")
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        st.error(str(e))
    
    # Cleanup
    os.unlink(temp_file_path)