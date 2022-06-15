package ch.persi.java.vino.excel;

import ch.persi.common.excel.ExcelUtil;
import ch.persi.java.vino.domain.WineOffering;
import org.apache.poi.ss.usermodel.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Map;
import org.apache.poi.openxml4j.exceptions.InvalidFormatException;
import static org.apache.commons.lang3.ArrayUtils.isEmpty;
import static org.apache.commons.lang3.StringUtils.isBlank;
import static org.apache.commons.lang3.StringUtils.isNotBlank;

public class VinoExcelUtil extends ExcelUtil {

	private static final String NON_RECORD_LINES_SHEET = "nonRecordLines";
	private static final String STRING_STYLE = "input_$";
	private static final String TITLE_STYLE = "title";
	private static final String DELIMITER = ";";

	private final Logger log = LoggerFactory.getLogger(getClass());

	private Sheet aSheet = null;
	private Sheet aNonRecordLinesSheet = null;
	private Workbook wb = null;
	private Map<String, CellStyle> styles;

	private int lastUsedRow = -1;
	private boolean headerDone;

	private String fileName = null;

	/**
	 * @param theSheetIdentifier the identifier of the sheet in the excel workbook
	 * @throws IOException if the Excel file can't be read
	 * @throws FileNotFoundException if the declared Excel file can't be found
	 */
	public void openStagingFile(final String theProviderCode, final String theSheetIdentifier) throws IOException, InvalidFormatException {
		if (isBlank(theSheetIdentifier)) {
			throw new IllegalArgumentException("SheetIdentifier and title row column headers must be provided !");
		}

		fileName = "vinoStagingFile" + theProviderCode + ".xlsx";

		wb = openFile(fileName);
		aSheet = getWorkSheet(wb, theSheetIdentifier);
		aSheet.setPrintGridlines(false);
		aSheet.setDisplayGridlines(true);
		styles = createStyles(wb);
	}

	private static String createComponentString(final WineOffering theWineOffering) {
		StringBuilder aBuilder = new StringBuilder(theWineOffering.getWine().toString());
		aBuilder.append(DELIMITER);
		String aWineUnit = theWineOffering.getWineUnit().toString();
		aBuilder.append(aWineUnit);
		aBuilder.append(DELIMITER);
		String anOffering = theWineOffering.getOffering().toString();
		aBuilder.append(anOffering);
		return aBuilder.toString().trim();
	}

	private Sheet getNonRecordLinesSheet() {
		aNonRecordLinesSheet = wb.getSheet(VinoExcelUtil.NON_RECORD_LINES_SHEET);
		if (aNonRecordLinesSheet == null) {
			aNonRecordLinesSheet = wb.createSheet(VinoExcelUtil.NON_RECORD_LINES_SHEET);
		}

		// initializing the index
		lastUsedRow = aNonRecordLinesSheet.getLastRowNum();
		return aNonRecordLinesSheet;
	}

	public void addSkippedRow(final String theRow) {
		aNonRecordLinesSheet = getNonRecordLinesSheet();

		Row aNewRow = createRow(aNonRecordLinesSheet);
		if (aNewRow == null) {
			throw new IllegalStateException("Adding a new rows to sheet '" + aNonRecordLinesSheet.getSheetName() + "' is not possible !");
		}

		aNewRow.createCell(0).setCellValue(theRow);
	}

	/**
	 * Dumps the passed objects to an Excel row in the staging file
	 *
	 * @param theWineOffering the WineOffering structure which is dumped as one additional row in an Excel sheet
	 */
	public void addRow(final WineOffering theWineOffering) {
		prepareTitleRow(theWineOffering);
		writeLine(createComponentString(theWineOffering).split(DELIMITER), 1, styles.get(STRING_STYLE));
	}

	private void writeLine(final String[] theComponents, final int theValueIndicator, final CellStyle theCellStyle) {
		Row aNewRow = aSheet.createRow(++lastUsedRow);

		for (int i = 0; i < theComponents.length; i++) {
			if (isNotBlank(theComponents[i])) {
				String[] someKeyValues = theComponents[i].split("=");
				Cell createCell = aNewRow.createCell(i);
				createCell.setCellValue((theValueIndicator <= someKeyValues.length) ? someKeyValues[theValueIndicator] : "");
				createCell.setCellStyle(theCellStyle);
			} else {
				log.error("At WriteLine, theComponents are obviously null, this is a serious problem !");
			}
		}
	}

	private Row createRow(final Sheet theSheet) {
		int aNewLineRowIndex = ++lastUsedRow;
		return theSheet.createRow(aNewLineRowIndex);
	}

	private void prepareTitleRow(final WineOffering theWineOffering) {

		if (aSheet == null) {
			throw new IllegalStateException("There is no sheet, can't write anything to a non openend excel worksheet !");
		}

		if (!headerDone) {
			String[] someComponents = createComponentString(theWineOffering).split(DELIMITER);
			if (!isEmpty(someComponents)) {
				writeLine(someComponents, 0, styles.get(TITLE_STYLE)); // this
				// should
				// write
				// the
				// title
				// row
				headerDone = true;
			}
		}
		/*
		 TODO: could assert here that wine offering structure remains the same
		 as with existing sheet
		*/
	}

	public void close() {
		if (!isBlank(fileName)) {
			try (FileOutputStream out = new FileOutputStream(fileName)) {
				if (wb != null) {
					out.flush();
					wb.write(out);
				}
			} catch (IOException e) {
				log.error("Closing the Excel Util caused a problem !", e);
			}

			aSheet = null;
			aNonRecordLinesSheet = null;
			wb = null;
		}
	}

}
