package ch.persi.wine.feed.priceservice.service;

import org.apache.poi.ss.usermodel.*;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

@Service
public class ExcelReaderService {

    public List<List<String>> readExcelFile(InputStream inputStream) {
        List<List<String>> data = new ArrayList<>();
        try (Workbook workbook = WorkbookFactory.create(inputStream)) {
            Sheet sheet = workbook.getSheetAt(0); // Nimm das erste Blatt

            for (Row row : sheet) {
                List<String> rowData = new ArrayList<>();
                for (Cell cell : row) {
                    switch (cell.getCellType()) {
                        case STRING -> rowData.add(cell.getStringCellValue());
                        case NUMERIC -> rowData.add(String.valueOf(cell.getNumericCellValue()));
                        default -> rowData.add("");
                    }
                }
                data.add(rowData);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return data;
    }
}
