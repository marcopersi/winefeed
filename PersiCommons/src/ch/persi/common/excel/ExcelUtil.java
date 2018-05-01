package ch.persi.common.excel;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.text.DateFormat;
import java.text.NumberFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.poi.hssf.usermodel.HSSFWorkbook;
import org.apache.poi.openxml4j.exceptions.InvalidFormatException;
import org.apache.poi.ss.usermodel.BorderStyle;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.CellStyle;
import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.ss.usermodel.FillPatternType;
import org.apache.poi.ss.usermodel.Font;
import org.apache.poi.ss.usermodel.HorizontalAlignment;
import org.apache.poi.ss.usermodel.IndexedColors;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;


public class ExcelUtil {

  private static final String STRING_STYLE = "input_$";
  private static final String TITLE_STYLE = "title";
  private InputStream excelFileToRead;

  /**
   * @throws IOException
   * @throws InvalidFormatException
   */
  public Workbook openFile(final String theFileName) throws IOException, InvalidFormatException {
    File aTargetFile = new File(theFileName);
    if (!aTargetFile.exists() || !aTargetFile.isFile()) {
      try (FileOutputStream aFileOutputStream = new FileOutputStream(theFileName)) {
        XSSFWorkbook aWorkBook = new XSSFWorkbook();
        aWorkBook.write(aFileOutputStream);
        return aWorkBook;
      }
    }

    Pattern compile = Pattern.compile("(.*)\\.(.*)");
    Matcher matcher = compile.matcher(theFileName);
    if (matcher.matches()) {
      if (matcher.group(2).equalsIgnoreCase("xlsx")) {
        return readXLSXFile(theFileName);
      }
      return readXLSFile(theFileName);
    }

    throw new UnsupportedOperationException("Received unrecognized file type, may deal only with XLS and XLSX files !");
  }

  public void close() {
    try {
      if (excelFileToRead != null) {
        excelFileToRead.close();
      }
    } catch (IOException ex) {
      ex.printStackTrace();
    }
  }

  private static Workbook readXLSFile(final String theFileName) throws IOException {
    return new HSSFWorkbook(new FileInputStream(new File(theFileName)));
  }

  private Workbook readXLSXFile(final String theFileName) throws IOException {
    excelFileToRead = new FileInputStream(theFileName);
    return new XSSFWorkbook(excelFileToRead);
  }

  public Sheet getWorkSheet(final Workbook theWorkBook, final String theSheetIdentifier) {
    Sheet aSheet = theWorkBook.getSheet(theSheetIdentifier);
    if (aSheet == null) {
      aSheet = theWorkBook.createSheet(theSheetIdentifier);
    }
    return aSheet;
  }

  /**
   * 
   * @param theCell
   *          is the HSSFCell
   * @return String representation of cells content
   */
  public static String getCellValue(final Cell theCell) {

    if (theCell == null) return null;

    switch (theCell.getCellTypeEnum()) {
      case BLANK:
        break;
      case NUMERIC:
        return evaluateNumberFormat(theCell);
      case STRING:
        return theCell.getStringCellValue().trim();
      default:
        break;
    }

    return null;
  }

  public static Double getNumericCellValueUnformatted(final Cell theCell) {
    if (theCell == null || theCell.getCellTypeEnum() != CellType.NUMERIC) {
      return null;
    }
    return theCell.getNumericCellValue();
  }

  private static String evaluateNumberFormat(final Cell theCell) {
    CellStyle cellStyle = theCell.getCellStyle();
    short dataFormat = cellStyle.getDataFormat();
    /*
     * assumption is made that dataFormat = 15, when cellType is
     * HSSFCell.CELL_TYPE_NUMERIC is equal to a DATE format.
     */
    if (dataFormat == 0) {
      NumberFormat aFormatter = NumberFormat.getInstance();
      aFormatter.setGroupingUsed(false); // no separators (as thousands...)
      return aFormatter.format(theCell.getNumericCellValue()).trim();
    } else if (dataFormat == 15 || dataFormat == 14 || dataFormat == 164) {
      SimpleDateFormat formatter = new SimpleDateFormat("dd.MM.yyyy");
      return formatter.format(theCell.getDateCellValue()).trim();
    } else if (dataFormat == 166) {
      SimpleDateFormat formatter = new SimpleDateFormat("dd/MM/yyyy");
      return formatter.format(theCell.getDateCellValue()).trim();
    } else {
      // check if date is feasible
      String stringCellValue = theCell.getStringCellValue();
      try {
        Date parse = DateFormat.getInstance().parse(stringCellValue);
        if (parse != null) {
          return DateFormat.getInstance().format(parse);
        }
      } catch (ParseException e) {
        System.out.println("The Cellvalue: '" + stringCellValue + " 'is definitely not a date, will be used as a number now !");

      }

    }

    // everything else
    return String.valueOf(theCell.getNumericCellValue()).trim();
  }

  /**
   * cell styles used for formatting calendar sheets
   */
  protected static Map<String, CellStyle> createStyles(final Workbook theWorkBook) {
    Map<String, CellStyle> styles = new HashMap<>();

    CellStyle style;
    Font titleFont = theWorkBook.createFont();
    titleFont.setFontHeightInPoints((short)14);
    titleFont.setFontName("Trebuchet MS");
    style = theWorkBook.createCellStyle();
    style.setFont(titleFont);
    style.setBorderBottom(BorderStyle.DOTTED);
    style.setBottomBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    styles.put(TITLE_STYLE, style);

    Font itemFont = theWorkBook.createFont();
    itemFont.setFontHeightInPoints((short)9);
    itemFont.setFontName("Trebuchet MS");
    style = theWorkBook.createCellStyle();
    style.setAlignment(HorizontalAlignment.LEFT);
    style.setFont(itemFont);
    styles.put("item_left", style);

    style = theWorkBook.createCellStyle();
    style.setAlignment(HorizontalAlignment.RIGHT);
    style.setFont(itemFont);
    styles.put("item_right", style);

    style = theWorkBook.createCellStyle();
    style.setAlignment(HorizontalAlignment.RIGHT);
    style.setFont(itemFont);
    style.setBorderRight(BorderStyle.DOTTED);
    style.setRightBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderBottom(BorderStyle.DOTTED);
    style.setBottomBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderLeft(BorderStyle.DOTTED);
    style.setLeftBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderTop(BorderStyle.DOTTED);
    style.setTopBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setDataFormat(theWorkBook.createDataFormat().getFormat("_($* #,##0.00_);_($* (#,##0.00);_($* \"-\"??_);_(@_)"));
    styles.put(STRING_STYLE, style);

    style = theWorkBook.createCellStyle();
    style.setAlignment(HorizontalAlignment.RIGHT);
    style.setFont(itemFont);
    style.setBorderRight(BorderStyle.DOTTED);
    style.setRightBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderBottom(BorderStyle.DOTTED);
    style.setBottomBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderLeft(BorderStyle.DOTTED);
    style.setLeftBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderTop(BorderStyle.DOTTED);
    style.setTopBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setDataFormat(theWorkBook.createDataFormat().getFormat("0.000%"));
    styles.put("input_%", style);

    style = theWorkBook.createCellStyle();
    style.setAlignment(HorizontalAlignment.RIGHT);
    style.setFont(itemFont);
    style.setBorderRight(BorderStyle.DOTTED);
    style.setRightBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderBottom(BorderStyle.DOTTED);
    style.setBottomBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderLeft(BorderStyle.DOTTED);
    style.setLeftBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderTop(BorderStyle.DOTTED);
    style.setTopBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setDataFormat(theWorkBook.createDataFormat().getFormat("0"));
    styles.put("input_i", style);

    style = theWorkBook.createCellStyle();
    style.setAlignment(HorizontalAlignment.CENTER);
    style.setFont(itemFont);
    style.setDataFormat(theWorkBook.createDataFormat().getFormat("m/d/yy"));
    styles.put("input_d", style);

    style = theWorkBook.createCellStyle();
    style.setAlignment(HorizontalAlignment.RIGHT);
    style.setFont(itemFont);
    style.setBorderRight(BorderStyle.DOTTED);
    style.setRightBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderBottom(BorderStyle.DOTTED);
    style.setBottomBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderLeft(BorderStyle.DOTTED);
    style.setLeftBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderTop(BorderStyle.DOTTED);
    style.setTopBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setDataFormat(theWorkBook.createDataFormat().getFormat("$##,##0.00"));
    style.setBorderBottom(BorderStyle.DOTTED);
    style.setBottomBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setFillForegroundColor(IndexedColors.GREY_25_PERCENT.getIndex());
    style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
    styles.put("formula_$", style);

    style = theWorkBook.createCellStyle();
    style.setAlignment(HorizontalAlignment.RIGHT);
    style.setFont(itemFont);
    style.setBorderRight(BorderStyle.DOTTED);
    style.setRightBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderBottom(BorderStyle.DOTTED);
    style.setBottomBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderLeft(BorderStyle.DOTTED);
    style.setLeftBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setBorderTop(BorderStyle.DOTTED);
    style.setTopBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setDataFormat(theWorkBook.createDataFormat().getFormat("0"));
    style.setBorderBottom(BorderStyle.DOTTED);
    style.setBottomBorderColor(IndexedColors.GREY_40_PERCENT.getIndex());
    style.setFillForegroundColor(IndexedColors.GREY_25_PERCENT.getIndex());
    style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
    styles.put("formula_i", style);

    return styles;
  }

  public Sheet getExcelSheet(final String theFileName, final String theSheetName) throws IOException, InvalidFormatException {

    Workbook aWorkBook = openFile(theFileName);

    if (aWorkBook == null) {
      throw new IllegalStateException("Didn't find a workbook for the given Excel file name '" + theFileName);
    }

    // getting the sheet out of the workbook.
    Sheet anExcelSourceFile = getWorkSheet(aWorkBook, theSheetName);

    if (anExcelSourceFile == null) {
      throw new IllegalStateException("Didn't find a sheet named '" + theSheetName + "' in the given excel workbook");
    }
    return anExcelSourceFile;
  }
}
