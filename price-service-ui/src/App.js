import React, { useState } from "react";
import axios from "axios";

function App() {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleFileUpload = async () => {
    if (!file) {
      alert("Please select a file to upload!");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("/api/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      alert(response.data);
    } catch (error) {
      console.error("Error uploading file:", error);
      alert("File upload failed!");
    }
  };

  const handleSearch = async () => {
    try {
      const response = await axios.get(`/prices/search?keyword=${query}`);
      setResults(response.data);
    } catch (error) {
      console.error("Error fetching data:", error);
      alert("Search failed!");
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Price Service UI</h1>

      <div>
        <h2>Upload Excel File</h2>
        <input type="file" onChange={handleFileChange} />
        <button onClick={handleFileUpload}>Upload</button>
      </div>

      <div style={{ marginTop: "20px" }}>
        <h2>Search Prices</h2>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter search query"
        />
        <button onClick={handleSearch}>Search</button>
      </div>

      <div style={{ marginTop: "20px" }}>
        <h2>Results</h2>
        {results.length > 0 ? (
          <ul>
            {results.map((result, index) => (
              <li key={index}>{JSON.stringify(result)}</li>
            ))}
          </ul>
        ) : (
          <p>No results found.</p>
        )}
      </div>
    </div>
  );
}

export default App;
