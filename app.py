import streamlit as st
import pandas as pd
import tempfile
import pdfplumber # Changed from tabula
import fitz  # PyMuPDF
import os
import json
import io
from PIL import Image

# Ensure you have pdfplumber installed: pip install pdfplumber pandas streamlit Pillow PyMuPDF

def convert_tables_to_json(tables):
    """Convert multiple pandas DataFrames into a single SurveyJS JSON format."""
    all_elements = []
    for idx, table_df in enumerate(tables):
        if not isinstance(table_df, pd.DataFrame):
            st.error(f"Item {idx+1} in tables list is not a DataFrame. Skipping.")
            continue
        if table_df.empty:
            st.warning(f"Table {idx+1} is empty. Skipping.")
            continue

        # Create column definitions
        # MODIFIED: Ensure 'name' for columns is never empty
        columns = []
        for i, col_header in enumerate(table_df.columns):
            col_name_str = str(col_header).strip() # Convert to string and strip whitespace
            if not col_name_str: # If column name is empty after stripping
                col_name_str = f"Unnamed_Column_{i+1}"
            
            columns.append({
                "name": col_name_str, 
                "title": str(col_header) if str(col_header).strip() else col_name_str, # Use original for title if not empty, else use the generated name
                "cellType": "text"
            })
        
        # Process rows
        row_data = {}
        rows_for_surveyjs = [] # SurveyJS expects a list of row identifiers/names
        for i_row in range(len(table_df)):
            row_name = f"Row {i_row + 1}"
            rows_for_surveyjs.append(row_name)
            current_row_values = {}
            for col_idx, col_original_header in enumerate(table_df.columns):
                # Use the same logic for accessing column data as used for defining column 'name'
                col_name_for_json = columns[col_idx]["name"] # Get the name used in JSON column definition
                cell_value = table_df.iloc[i_row][col_original_header]
                current_row_values[col_name_for_json] = str(cell_value) if pd.notna(cell_value) else ""
            row_data[row_name] = current_row_values
        
        # Create element for this table
        element = {
            "type": "matrixdropdown",
            "name": f"Table {idx + 1}",
            "title": f"Details for Table {idx + 1}", # Added a title for clarity in SurveyJS
            "defaultValue": row_data,
            "columns": columns,
            "rows": rows_for_surveyjs # Use the generated list of row names
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
st.set_page_config(layout="wide") # Use wider layout for better table display
st.title("📄 PDF Table Extractor & JSON Converter")
st.markdown("""
Upload a PDF file to extract tables. You can then preview the PDF, view extracted tables,
trim rows, edit data, split tables, and finally convert them into SurveyJS JSON format or download as CSV.
""")

# Upload PDF
uploaded_file = st.file_uploader("📂 Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        temp_file_path = temp_file.name

    st.sidebar.header("📄 PDF Preview")
    try:
        pdf_document = fitz.open(temp_file_path)
        if len(pdf_document) == 0:
            st.sidebar.warning("The PDF is empty or could not be read for preview.")
        else:
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                # Render page to an image (adjust DPI for performance vs quality)
                # Using 150 DPI for a balance
                pix = page.get_pixmap(matrix=fitz.Matrix(150/72, 150/72)) 
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                st.sidebar.image(img, caption=f"Page {page_num+1}", use_container_width=True)
        pdf_document.close()
    except Exception as preview_error:
        st.sidebar.error(f"Error previewing PDF: {preview_error}")
    
    st.header("📊 Extracted Tables & Operations")
    try:
        extracted_tables_dfs = []
        with pdfplumber.open(temp_file_path) as pdf:
            if not pdf.pages:
                st.warning("The PDF contains no pages or could not be parsed by pdfplumber.")
            for page_num, page in enumerate(pdf.pages):
                # extract_tables() returns a list of tables found on the page.
                # Each table is a list of rows, and each row is a list of cell contents.
                page_tables_data = page.extract_tables()
                if not page_tables_data:
                    st.info(f"No tables found on page {page_num + 1}.")
                    continue
                
                st.write(f"Found {len(page_tables_data)} table(s) on page {page_num + 1}:")
                for table_idx, table_data in enumerate(page_tables_data):
                    if table_data:  # If table data is not empty
                        # Convert list of lists to DataFrame
                        header = table_data[0]
                        # Ensure header is a list of strings, replacing None with placeholders
                        # MODIFIED: Ensure column headers are unique and not empty for DataFrame creation
                        columns_df = []
                        temp_col_names = set()
                        for i, h in enumerate(header):
                            col_name = str(h).strip() if h is not None else ""
                            if not col_name: # If empty or None
                                col_name = f"Extracted_Column_{i+1}"
                            
                            # Ensure uniqueness for DataFrame columns
                            original_col_name = col_name
                            count = 1
                            while col_name in temp_col_names:
                                col_name = f"{original_col_name}_{count}"
                                count += 1
                            temp_col_names.add(col_name)
                            columns_df.append(col_name)
                        
                        data_rows = table_data[1:]
                        
                        if not data_rows and not columns_df: # Completely empty table
                            df = pd.DataFrame()
                        elif not data_rows: # Table with only header
                             df = pd.DataFrame(columns=columns_df)
                        else: # Table with header and data
                            df = pd.DataFrame(data_rows, columns=columns_df)
                        
                        df = df.fillna("") # Replace NaN/None with empty strings for consistency
                        extracted_tables_dfs.append(df)
                    else:
                        st.info(f"An empty table structure was detected on page {page_num + 1}, table {table_idx +1}.")


        if extracted_tables_dfs:
            st.success(f"Successfully extracted {len(extracted_tables_dfs)} table(s) from the PDF.")
            
            # For simplicity, we'll focus UI operations on the first extracted table.
            # You could extend this to select which table to operate on if multiple are found.
            df_to_operate = extracted_tables_dfs[0].copy() 
            
            st.subheader("🔬 Preview and Edit First Extracted Table")
            st.info("The operations below (trim, edit, split) apply to the *first* table extracted from the PDF.")
            st.dataframe(df_to_operate)

            # Trim rows slider
            st.subheader("✂️ Trim Rows")
            if not df_to_operate.empty:
                trim_range = st.slider(
                    "Select range of rows to keep (for the first table):",
                    0, len(df_to_operate)-1, (0, len(df_to_operate)-1) if len(df_to_operate) > 0 else (0,0),
                    key="trim_slider"
                )
                trimmed_df = df_to_operate.iloc[trim_range[0]:trim_range[1]+1]
            else:
                st.warning("Cannot trim an empty table.")
                trimmed_df = df_to_operate.copy()

            st.subheader("✏️ Editable Table (Trimmed)")
            if not trimmed_df.empty:
                edited_df = st.data_editor(trimmed_df, num_rows="dynamic")
            else:
                st.warning("Trimmed table is empty, cannot edit.")
                edited_df = trimmed_df.copy()
            
            st.subheader("쪼개다 Split Table") # "쪼개다" means "split" in Korean, as per original comment style
            if not edited_df.empty:
                num_splits = st.number_input("Enter number of parts to split the table into:", 
                                           min_value=1, 
                                           max_value=len(edited_df) if len(edited_df) > 0 else 1, 
                                           value=1)
                
                split_points_input = []
                if num_splits > 1:
                    st.write("Define row indices where splits should occur (0-indexed). The table will be split *before* these rows.")
                    # Help text for split points
                    st.caption(f"Enter {num_splits - 1} split points. For example, to split a 10-row table into 3 parts, you might enter 2 split points like 3 and 7. This creates tables of rows 0-2, 3-6, and 7-9.")

                    cols = st.columns(num_splits - 1)
                    for i in range(num_splits - 1):
                        with cols[i]:
                            default_split_val = int((i + 1) * len(edited_df) / num_splits)
                            # Ensure default_split_val is within valid range
                            default_split_val = max(1, min(default_split_val, len(edited_df) -1))

                            split_idx = st.number_input(
                                f"Split after row index for part {i+1} (ends part {i+1}):",
                                min_value=0,  # Min is 0 (start of table)
                                max_value=len(edited_df) - 2 if len(edited_df) > 1 else 0, # Max is second to last row
                                value=default_split_val -1 if default_split_val > 0 else 0, # Adjust default to be "after row index"
                                key=f"split_point_{i}"
                            )
                            split_points_input.append(split_idx + 1) # Convert "after row" to "start of next table"
                
                # Sort and unique split points, then add start and end boundaries
                split_points = sorted(list(set([0] + split_points_input + [len(edited_df)])))
                # Remove any split points outside the bounds or duplicates that might cause empty DFs
                split_points = [sp for i, sp in enumerate(split_points) if sp >=0 and sp <= len(edited_df) and (i == 0 or sp > split_points[i-1])]


                split_tables = []
                for i in range(len(split_points)-1):
                    start_row = split_points[i]
                    end_row = split_points[i+1]
                    if start_row < end_row : # Ensure valid slice
                         split_tables.append(edited_df.iloc[start_row:end_row])
                
                if not split_tables and not edited_df.empty: # If splitting resulted in no tables but original was not empty
                    st.warning("Splitting configuration resulted in no valid tables. Using the edited table as a single part.")
                    split_tables = [edited_df.copy()]
                elif not split_tables and edited_df.empty:
                    st.info("Original table is empty, so no split tables generated.")


                for idx, new_table in enumerate(split_tables):
                    if not new_table.empty:
                        st.subheader(f"Split Table Part {idx+1}")
                        st.dataframe(new_table)
                        
                        # Download CSV option
                        csv = new_table.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label=f"📥 Download Part {idx+1} (CSV)", 
                            data=csv, 
                            file_name=f"split_table_part_{idx+1}.csv", 
                            mime="text/csv",
                            key=f"csv_download_{idx}"
                        )
                    else:
                        st.info(f"Split Table Part {idx+1} is empty.")
            else:
                st.warning("Cannot split an empty table.")
                split_tables = [] # Ensure split_tables is defined
            
            # Convert all split tables (derived from the first extracted table) to single JSON
            if split_tables:
                combined_json = convert_tables_to_json(split_tables)
                
                st.header("📜 Combined SurveyJS JSON Output")
                st.markdown("This JSON combines the (potentially split) parts of the *first* extracted table.")
                st.markdown("[Test your JSON in SurveyJS Creator](https://surveyjs.io/create-free-survey)")
                st.json(combined_json)
                
                json_str = json.dumps(combined_json, indent=2).encode('utf-8')
                st.download_button(
                    label="📥 Download Combined JSON",
                    data=json_str,
                    file_name="surveyjs_tables.json",
                    mime="application/json",
                    key="json_download_combined"
                )
            elif not edited_df.empty: # If there were no splits, but there was an edited table
                st.info("No splits were made, or splits resulted in empty tables. Converting the edited table as a single unit.")
                combined_json = convert_tables_to_json([edited_df.copy()]) # Convert the single edited table
                st.header("📜 SurveyJS JSON Output (Single Table)")
                st.markdown("[Test your JSON in SurveyJS Creator](https://surveyjs.io/create-free-survey)")
                st.json(combined_json)
                json_str = json.dumps(combined_json, indent=2).encode('utf-8')
                st.download_button(
                    label="📥 Download JSON (Single Table)",
                    data=json_str,
                    file_name="surveyjs_table.json",
                    mime="application/json",
                    key="json_download_single"
                )
            else:
                st.info("No tables to convert to JSON.")

        else:
            st.warning("No tables were found in the PDF using pdfplumber.")
    except Exception as e:
        st.error(f"An error occurred during table processing: {e}")
        # For more detailed debugging, you might want to log the traceback
        # import traceback
        # st.error(traceback.format_exc())
    
    # Cleanup
    try:
        os.unlink(temp_file_path)
    except Exception as e:
        st.warning(f"Could not delete temporary file {temp_file_path}: {e}")

else:
    st.info("Please upload a PDF file to begin.")

st.markdown("---")
st.markdown("Made with ❤️ using Streamlit and Pdfplumber.")
