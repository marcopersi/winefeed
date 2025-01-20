package ch.persi.wine.feed.priceservice.controller;

import ch.persi.wine.feed.priceservice.data.PriceData;
import ch.persi.wine.feed.priceservice.repository.PriceDataRepository;
import ch.persi.wine.feed.priceservice.service.ExcelReaderService;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;

@RestController
@RequestMapping("/api/upload")
public class FileUploadController {

    private final ExcelReaderService excelReaderService;
    private final PriceDataRepository repository;

    public FileUploadController(ExcelReaderService excelReaderService, PriceDataRepository repository) {
        this.excelReaderService = excelReaderService;
        this.repository = repository;
    }

    @PostMapping
    public String uploadFile(@RequestParam("file") MultipartFile file) {
        try {
            List<List<String>> data = excelReaderService.readExcelFile(file.getInputStream());

            // Daten in die Datenbank speichern
            for (List<String> row : data) {
                PriceData priceData = new PriceData();
                priceData.setColumn1(row.get(0));
                priceData.setColumn2(row.size() > 1 ? row.get(1) : "");
                repository.save(priceData);
            }

            return "File uploaded and data saved successfully!";
        } catch (IOException e) {
            e.printStackTrace();
            return "Error processing file: " + e.getMessage();
        }
    }
}
