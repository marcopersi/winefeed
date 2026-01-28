package ch.persi.java.pdfbox.test;

import java.io.IOException;
import java.math.BigDecimal;
import java.util.Date;

import junit.framework.TestCase;
import ch.persi.java.vino.domain.Offering;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.domain.Wine;
import ch.persi.java.vino.domain.WineOffering;
import ch.persi.java.vino.excel.ExcelUtil;

public class ExcelTest extends TestCase {

	
	public void testAddRow() throws IOException
	{
		WineOffering anOffering = new WineOffering(new Wine(2006,"MO/DOC","Masseto", "Toskana", "Tenuta dell'Ornellaia"),new Unit(new BigDecimal(7.5)), new Offering(new Provider("Wermuth"),"1",new BigDecimal(300), new BigDecimal(600), new Date(), true, 6));
		
		ExcelUtil excelFileHandle = new ExcelUtil();
		excelFileHandle.openStagingFile("testfile");
		excelFileHandle.addRow(anOffering);
		excelFileHandle.close();
	}

	public void testWriteWithoutOpenFile()
	{
		try
		{
			WineOffering anOffering = new WineOffering(new Wine(2006,"MO/DOC","Masseto", "Toskana", "Tenuta dell'Ornellaia"),new Unit(new BigDecimal(7.5)), new Offering(new Provider("Wermuth"),"1",new BigDecimal(300), new BigDecimal(600), new Date(), true, 6));
			ExcelUtil excelFileHandle = new ExcelUtil();
			excelFileHandle.addRow(anOffering);
		} catch(IllegalStateException e)
		{
			// expected
		} catch(Throwable t)
		{
			fail(t.getLocalizedMessage());
		}
	}
	
	// TODO: missing tests:
	/*
	 * 1. finding last used Row
	 * 2. do not overwrite existing lines in a sheet test
	 * 
	 * 
	 * 
	 */
	
}
