import { useState, useRef } from 'react';
import * as Plotly from 'plotly';
import _ from 'lodash';

// PDF Table Extractor Component
export default function PDFTableExtractor() {
  // State variables
  const [pdfFile, setPdfFile] = useState(null);
  const [pdfPreview, setPdfPreview] = useState([]);
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [trimRange, setTrimRange] = useState([0, 0]);
  const [numSplits, setNumSplits] = useState(1);
  const [splitPoints, setSplitPoints] = useState([0]);
  const [splitTables, setSplitTables] = useState([]);
  const [jsonOutput, setJsonOutput] = useState(null);
  const fileInputRef = useRef(null);

  // Handle file upload
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
      setPdfFile(file);
      // Mock preview generation (in a real app, you'd use a PDF library)
      generatePdfPreview(file);
      extractTables(file);
    } else {
      setError("Please upload a valid PDF file");
    }
  };

  // Mock function to generate PDF preview (would use pdf.js in a real app)
  const generatePdfPreview = (file) => {
    setPdfPreview([
      { id: 1, placeholder: true },
      { id: 2, placeholder: true }
    ]);
  };

  // Mock function to extract tables (would use a backend service in a real app)
  const extractTables = (file) => {
    setLoading(true);
    
    // Simulate API call with setTimeout
    setTimeout(() => {
      try {
        // Mock data - in a real app this would come from your backend
        const mockTableData = {
          columns: ["Item", "Quantity", "Price", "Total"],
          data: [
            ["Laptop", "1", "$1200", "$1200"],
            ["Mouse", "2", "$25", "$50"],
            ["Keyboard", "1", "$80", "$80"],
            ["Monitor", "2", "$300", "$600"],
            ["Headphones", "1", "$150", "$150"],
          ]
        };
        
        // Create dataframe-like structure
        const extractedTable = {
          columns: mockTableData.columns,
          data: mockTableData.data,
          get length() { return this.data.length; }
        };
        
        setTables([extractedTable]);
        setTrimRange([0, extractedTable.length - 1]);
        updateSplitTables([extractedTable]);
        setLoading(false);
      } catch (err) {
        setError("Error extracting tables: " + err.message);
        setLoading(false);
      }
    }, 1500);
  };

  // Update trim range
  const handleTrimRangeChange = (newRange) => {
    setTrimRange(newRange);
    
    if (tables.length > 0) {
      const trimmedTable = {
        columns: tables[0].columns,
        data: tables[0].data.slice(newRange[0], newRange[1] + 1),
        get length() { return this.data.length; }
      };
      
      updateSplitTables([trimmedTable]);
    }
  };

  // Update number of splits
  const handleNumSplitsChange = (value) => {
    setNumSplits(value);
    
    if (tables.length > 0) {
      const trimmedTableLength = trimRange[1] - trimRange[0] + 1;
      const newSplitPoints = [0];
      
      for (let i = 1; i < value; i++) {
        newSplitPoints.push(Math.floor(i * trimmedTableLength / value));
      }
      
      newSplitPoints.push(trimmedTableLength);
      setSplitPoints(newSplitPoints);
      
      const trimmedTable = {
        columns: tables[0].columns,
        data: tables[0].data.slice(trimRange[0], trimRange[1] + 1),
        get length() { return this.data.length; }
      };
      
      splitTableBasedOnPoints(trimmedTable, newSplitPoints);
    }
  };

  // Update split point
  const handleSplitPointChange = (index, value) => {
    const newSplitPoints = [...splitPoints];
    newSplitPoints[index] = value;
    setSplitPoints(newSplitPoints);
    
    if (tables.length > 0) {
      const trimmedTable = {
        columns: tables[0].columns,
        data: tables[0].data.slice(trimRange[0], trimRange[1] + 1),
        get length() { return this.data.length; }
      };
      
      splitTableBasedOnPoints(trimmedTable, newSplitPoints);
    }
  };

  // Split the table based on split points
  const splitTableBasedOnPoints = (table, points) => {
    const splits = [];
    
    for (let i = 0; i < points.length - 1; i++) {
      splits.push({
        columns: table.columns,
        data: table.data.slice(points[i], points[i + 1]),
        get length() { return this.data.length; }
      });
    }
    
    setSplitTables(splits);
    generateJsonOutput(splits);
  };

  // Update split tables
  const updateSplitTables = (newTables) => {
    setSplitTables(newTables);
    generateJsonOutput(newTables);
  };

  // Generate JSON output
  const generateJsonOutput = (tableArray) => {
    const jsonData = convertTablesToJson(tableArray);
    setJsonOutput(jsonData);
  };

  // Convert tables to JSON (similar to your original function)
  const convertTablesToJson = (tables) => {
    const all_elements = [];
    
    for (let idx = 0; idx < tables.length; idx++) {
      const table = tables[idx];
      
      // Create column definitions
      const columns = table.columns.map(col => ({
        name: col,
        title: col,
        cellType: "text"
      }));
      
      // Process rows
      const rowData = {};
      const rows = [];
      
      for (let i = 0; i < table.data.length; i++) {
        const rowName = `Row ${i + 1}`;
        rows.push(rowName);
        
        rowData[rowName] = {};
        for (let j = 0; j < table.columns.length; j++) {
          const colName = table.columns[j];
          const cellValue = table.data[i][j];
          rowData[rowName][colName] = cellValue || "";
        }
      }
      
      // Create element for this table
      const element = {
        type: "matrixdropdown",
        name: `Table ${idx + 1}`,
        defaultValue: rowData,
        columns: columns,
        rows: rows
      };
      
      all_elements.push(element);
    }
    
    // Combine all elements into final JSON structure
    return {
      pages: [
        {
          name: "page1",
          elements: all_elements
        }
      ]
    };
  };

  // Download CSV
  const downloadCsv = (tableIndex) => {
    if (splitTables.length <= tableIndex) return;
    
    const table = splitTables[tableIndex];
    let csvContent = table.columns.join(',') + '\n';
    
    table.data.forEach(row => {
      csvContent += row.join(',') + '\n';
    });
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `split_table_${tableIndex + 1}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Download JSON
  const downloadJson = () => {
    if (!jsonOutput) return;
    
    const jsonStr = JSON.stringify(jsonOutput, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'combined_tables.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <header className="bg-blue-600 text-white p-4 shadow-md">
        <h1 className="text-2xl font-bold">PDF Table Extractor & JSON Converter</h1>
      </header>
      
      <main className="flex-grow p-6 max-w-6xl mx-auto w-full">
        {/* File Upload Section */}
        <div className="mb-8 bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4">Upload PDF</h2>
          <div className="flex items-center">
            <input
              type="file"
              accept="application/pdf"
              onChange={handleFileUpload}
              className="hidden"
              ref={fileInputRef}
            />
            <button 
              onClick={() => fileInputRef.current.click()}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
            >
              Choose PDF File
            </button>
            <span className="ml-4 text-gray-600">
              {pdfFile ? pdfFile.name : "No file selected"}
            </span>
          </div>
        </div>
        
        {error && (
          <div className="mb-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}
        
        {loading && (
          <div className="flex justify-center my-8">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
            <span className="ml-2">Processing PDF...</span>
          </div>
        )}
        
        {/* PDF Preview Section */}
        {pdfPreview.length > 0 && (
          <div className="mb-8 bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4">PDF Preview</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {pdfPreview.map((page) => (
                <div key={page.id} className="border border-gray-300 rounded-md p-2">
                  {page.placeholder ? (
                    <div className="flex items-center justify-center bg-gray-100 h-64 w-full">
                      <p className="text-gray-500">Page {page.id} Preview</p>
                    </div>
                  ) : (
                    <img 
                      src={page.imageUrl || "/api/placeholder/400/320"} 
                      alt={`Page ${page.id}`}
                      className="max-w-full h-auto"
                    />
                  )}
                  <p className="text-center mt-2 text-sm text-gray-600">Page {page.id}</p>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Table Processing Section */}
        {tables.length > 0 && (
          <div className="mb-8 bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4">Table Processing</h2>
            
            {/* Trim Range Section */}
            <div className="mb-6">
              <h3 className="font-medium mb-2">Trim rows from top and bottom:</h3>
              <div className="flex flex-col md:flex-row items-center gap-4">
                <div className="w-full md:w-2/3">
                  <input
                    type="range"
                    min="0"
                    max={tables[0].length - 1}
                    value={trimRange[0]}
                    onChange={(e) => handleTrimRangeChange([parseInt(e.target.value), trimRange[1]])}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-600">
                    <span>0</span>
                    <span>{tables[0].length - 1}</span>
                  </div>
                </div>
                <span className="text-sm">Start row: {trimRange[0]}</span>
              </div>
              
              <div className="flex flex-col md:flex-row items-center gap-4 mt-4">
                <div className="w-full md:w-2/3">
                  <input
                    type="range"
                    min="0"
                    max={tables[0].length - 1}
                    value={trimRange[1]}
                    onChange={(e) => handleTrimRangeChange([trimRange[0], parseInt(e.target.value)])}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-600">
                    <span>0</span>
                    <span>{tables[0].length - 1}</span>
                  </div>
                </div>
                <span className="text-sm">End row: {trimRange[1]}</span>
              </div>
            </div>
            
            {/* Split Table Section */}
            <div className="mb-6">
              <h3 className="font-medium mb-2">Split table:</h3>
              <div className="flex flex-col md:flex-row items-center gap-4">
                <label className="text-sm">Number of splits:</label>
                <input
                  type="number"
                  min="1"
                  max={tables[0].length}
                  value={numSplits}
                  onChange={(e) => handleNumSplitsChange(parseInt(e.target.value))}
                  className="border border-gray-300 rounded px-3 py-2 w-24"
                />
              </div>
              
              {numSplits > 1 && (
                <div className="mt-4 space-y-3">
                  {Array.from({ length: numSplits - 1 }).map((_, idx) => (
                    <div key={idx} className="flex flex-col md:flex-row items-center gap-4">
                      <label className="text-sm">Split point {idx + 1}:</label>
                      <input
                        type="number"
                        min="0"
                        max={tables[0].length - 1}
                        value={splitPoints[idx + 1] || 0}
                        onChange={(e) => handleSplitPointChange(idx + 1, parseInt(e.target.value))}
                        className="border border-gray-300 rounded px-3 py-2 w-24"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Split Tables Display */}
        {splitTables.length > 0 && (
          <div className="mb-8">
            {splitTables.map((table, idx) => (
              <div key={idx} className="mb-6 bg-white p-6 rounded-lg shadow-md">
                <h2 className="text-xl font-semibold mb-4">Split Table {idx + 1}</h2>
                <div className="overflow-x-auto">
                  <table className="min-w-full bg-white border border-gray-300">
                    <thead>
                      <tr className="bg-gray-100">
                        {table.columns.map((col, colIdx) => (
                          <th key={colIdx} className="py-2 px-4 border-b text-left">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {table.data.map((row, rowIdx) => (
                        <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-gray-50' : ''}>
                          {row.map((cell, cellIdx) => (
                            <td key={cellIdx} className="py-2 px-4 border-b">
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-4">
                  <button
                    onClick={() => downloadCsv(idx)}
                    className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
                  >
                    Download Split Table {idx + 1} (CSV)
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* JSON Output */}
        {jsonOutput && (
          <div className="mb-8 bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4">Combined JSON Output</h2>
            <div className="mb-4">
              <a 
                href="https://surveyjs.io/create-free-survey" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-500 hover:underline"
              >
                Test your JSON in SurveyJS Creator
              </a>
            </div>
            <div className="bg-gray-100 p-4 rounded overflow-auto max-h-96">
              <pre className="text-sm">
                {JSON.stringify(jsonOutput, null, 2)}
              </pre>
            </div>
            <div className="mt-4">
              <button
                onClick={downloadJson}
                className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
              >
                Download Combined JSON
              </button>
            </div>
          </div>
        )}
      </main>
      
      <footer className="bg-gray-800 text-white p-4 text-center">
        <p>PDF Table Extractor & JSON Converter</p>
      </footer>
    </div>
  );
}