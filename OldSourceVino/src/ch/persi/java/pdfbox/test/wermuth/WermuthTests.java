package ch.persi.java.pdfbox.test.wermuth;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import junit.framework.TestCase;

import org.joda.time.DateTime;

import ch.persi.java.vino.importers.wermuth.WermuthImportTask;
import ch.persi.java.vino.util.iTextUtil;


public class WermuthTests extends TestCase {

    // BackLog short term (ordered)
    // ***************************

	// FIXME: consider that for example today failing test at steinfels: could apply match for amount of bottle, but there is no vintage at all, no wine ,no region
	// so consider really the minimum as record line pattern, then just make sure consistency , meaning all get.. Tests have to fail for a specific 'corrupt' line
	
	// FIXME: Impl for excel staging
	
	// FIXME: extend testCases for isRecordLine
	
	// FIXME: realized prices are too many times empty, there must be something wrong
    // use file by file import
    
	// FIXME: try to download new file based on a job definition, automate end to end process  
    
	// FIXME: log config, need fileappender or similar
    
	// FIXME consider View(er) pattern for views, consider
    // to apply a queue for jobs, fired on Quartz or use queue with skype connector to apply a new parse job.

	// FIXME: enrich stamm daten with region for wine (...Tenuta San Guide, Bolgheri for Sassicaia ; Pauillac, Bordeaux for Petrus,....)
    
    // Backlog (ideas) long term (unordered)
    // ************************************
    // 1. design the view / GUI
    // 2. create subversion / GIT repository (local git is done)
    // 3. set up hudson
    // 4. use TASK VIEW for error log
    // 4. 
       
    public void testGetAuctionDate() throws Exception
    {
    	List<String> someLines = iTextUtil.getLines("import/Wermuth/Weinauktion_WZ_223.pdf"); 
    	DateTime aDate = new WermuthImportTask().getAuctionDate(someLines);
    	assertNotNull(aDate);
    }
    
    public void testIsRecordLine()
    {
    	String[] someRecordLines = new String[]{"1 1 Magnumflasche 1995, pro Lot Sfr. 340-500",
    			"16 1 Doppelmagnumflasche, 1997, OHK pro Lot Sfr. 500-700",
    	    	"169 1 Imperialflasche, 2007, OHK pro Lot Sfr. 800-1200",
    	    	"174 3 Flaschen, 2001 pro Lot Sfr. 1800-2100",
    	    	"185 1 Flasche, 2008 pro Dz. Sfr. 1200-1800",
    	    	"187 1 Dutzend Flaschen, 2008, OHK pro Dz. Sfr. 900-1200",
    	    	"230 1 Dutzend Flaschen, 1997, 6er OHK pro Dz. Sfr. 840-1080",
    	    	"246 1 Impérialflasche, 2000, OHK pro Lot Sfr. 1200-1500",
    	    	"252 1 Jeroboamflasche, 1990, OHK pro Lot Sfr. 2400-3000",
    	    	"323 2 3/8 Flaschen, 2000 pro Lot Sfr. 200-350",
    	    	"334 6 Flaschen, 2002, OC pro Lot Sfr. 360-480",
    	    	"486 12 3/8 Flaschen, 2001, OHK pro Lot Sfr. 390-480",
    	    	"583 6 Flaschen, 2005, 3er OHK pro Lot Sfr. 540-720",
    	    	"984 2 Flaschen, 1966 pro Lot Sfr. 300-500",
    	    	"326 Total 6 3/8 Flaschen, 1998 pro Lot Sfr. 480-720"};
    	
    	WermuthImportTask wermuthImportTask = new WermuthImportTask();
    	for (String aTestRecordLine : someRecordLines) {
			boolean recordLine = wermuthImportTask.isRecordLine(aTestRecordLine);
    		assertTrue(aTestRecordLine + " isn't recognized as recordLine !", recordLine);
		}
    }

    public void testGetProducer()
    {
    	String aTestOriginContainingProducerLine = "MO/DOC, Toscana, Cantina Constanti";
    	assertNotNull(new WermuthImportTask().getProducer("MO/DOC",aTestOriginContainingProducerLine));
    }
    
    public void testGetOrigin()
    {
    	String aMODOCOrigin = "MO/DOC, Toscana, Cantina Constanti";
    	assertEquals("MO/DOC", new WermuthImportTask().getOrigin(aMODOCOrigin));
    	
    	String aMOIGTOrigin = "MO/IGT, Toscana, Antinori";
    	assertEquals("MO/IGT", new WermuthImportTask().getOrigin(aMOIGTOrigin));
    	
    	String aMoDOCGOrigin = "MO/DOCG, Piemont, Aldo Conterno";
    	assertEquals("MO/DOCG", new WermuthImportTask().getOrigin(aMoDOCGOrigin));

        String aMOOrigin = "MO, Napa Valley, Mondavi/Rothschild";
    	assertEquals("MO", new WermuthImportTask().getOrigin(aMOOrigin));

        String aACMCOrigin = "AC/MC, Margaux, 1er grand cru classe";
    	assertEquals("AC/MC", new WermuthImportTask().getOrigin(aACMCOrigin));

        String aDOMOOrigin = "DO/MO, Priorat, Alvaro Palacio";
    	assertEquals("DO/MO", new WermuthImportTask().getOrigin(aDOMOOrigin));
    	
    	String aACEAOrigin = "AC/EA, Rheingau, Weingut Dönnhoff";
    	assertEquals("AC/EA", new WermuthImportTask().getOrigin(aACEAOrigin));
    	
    	String anACMOOrigin = "AC/MO, Champagne, Armand de Brignac (Cattier)";
    	assertEquals("AC/MO", new WermuthImportTask().getOrigin(anACMOOrigin));
    }

    public void testGetNoOfBottles()
    {
    	Map<String,Integer> linesAndAssertValues = new HashMap<String,Integer>();
    	
    	linesAndAssertValues.put("116 1 Magnumflasche 1995, pro Lot Sfr. 340–500", 1);
    	linesAndAssertValues.put("168 1 Doppelmagnumflasche, 1997, OHK pro Lot Sfr. 500–700", 1);
    	linesAndAssertValues.put("169 1 Imperialflasche, 2007, OHK pro Lot Sfr. 800–1200", 1);
    	linesAndAssertValues.put("174 3 Flaschen, 2001 pro Lot Sfr. 1800–2100", 3);
    	linesAndAssertValues.put("185 1 Flasche, 2008 pro Dz. Sfr. 1200–1800", 1);
    	linesAndAssertValues.put("187 1 Dutzend Flaschen, 2008, OHK pro Dz. Sfr. 900–1200", 12);
    	linesAndAssertValues.put("230 1 Dutzend Flaschen, 1997, 6er OHK pro Dz. Sfr. 840–1080", 12);
    	linesAndAssertValues.put("246 1 Impérialflasche, 2000, OHK pro Lot Sfr. 1200–1500", 1);
    	linesAndAssertValues.put("252 1 Jeroboamflasche, 1990, OHK pro Lot Sfr. 2400–3000", 1);
    	linesAndAssertValues.put("323 2 3/8 Flaschen, 2000 pro Lot Sfr. 200–350", 2);
    	linesAndAssertValues.put("334 6 Flaschen, 2002, OC pro Lot Sfr. 360–480", 6);
    	linesAndAssertValues.put("486 12 3/8 Flaschen, 2001, OHK pro Lot Sfr. 390–480",12);
    	linesAndAssertValues.put("583 6 Flaschen, 2005, 3er OHK pro Lot Sfr. 540–720",6);
    	linesAndAssertValues.put("984 2 Flaschen, 1966 pro Lot Sfr. 300–500", 2);
    	linesAndAssertValues.put("326 Total 6 3/8 Flaschen, 1998 pro Lot Sfr. 480–720",6);
    
    	WermuthImportTask wermuthImportTask = new WermuthImportTask();
    	for (Entry<String, Integer> aTestEntry : linesAndAssertValues.entrySet()) {
			assertEquals(aTestEntry.getValue(),wermuthImportTask.getNoOfBottles(aTestEntry.getKey()));
		}  
    }
    
    public void testGetVintage()
    {
    	Map<String,Integer> linesAndAssertValues = new HashMap<String,Integer>();
    	
    	linesAndAssertValues.put("116 1 Magnumflasche 1995, pro Lot Sfr. 340–500", 1995);
    	linesAndAssertValues.put("168 1 Doppelmagnumflasche, 1997, OHK pro Lot Sfr. 500–700", 1997);
    	linesAndAssertValues.put("169 1 Imperialflasche, 2007, OHK pro Lot Sfr. 800–1200", 2007);
    	linesAndAssertValues.put("174 3 Flaschen, 2001 pro Lot Sfr. 1800–2100", 2001);
    	linesAndAssertValues.put("185 1 Flasche, 2008 pro Dz. Sfr. 1200–1800", 2008);
    	linesAndAssertValues.put("187 1 Dutzend Flaschen, 2008, OHK pro Dz. Sfr. 900–1200", 2008);
    	linesAndAssertValues.put("230 1 Dutzend Flaschen, 1997, 6er OHK pro Dz. Sfr. 840–1080", 1997);
    	linesAndAssertValues.put("246 1 Impérialflasche, 2000, OHK pro Lot Sfr. 1200–1500", 2000);
    	linesAndAssertValues.put("252 1 Jeroboamflasche, 1990, OHK pro Lot Sfr. 2400–3000", 1990);
    	linesAndAssertValues.put("323 2 3/8 Flaschen, 2000 pro Lot Sfr. 200–350", 2000);
    	linesAndAssertValues.put("334 6 Flaschen, 2002, OC pro Lot Sfr. 360–480", 2002);
    	linesAndAssertValues.put("486 12 3/8 Flaschen, 2001, OHK pro Lot Sfr. 390–480",2001);
    	linesAndAssertValues.put("583 6 Flaschen, 2005, 3er OHK pro Lot Sfr. 540–720",2005);
    	linesAndAssertValues.put("984 2 Flaschen, 1966 pro Lot Sfr. 300–500", 1966);
    	linesAndAssertValues.put("326 Total 6 3/8 Flaschen, 1998 pro Lot Sfr. 480–720",1998);
    
    	WermuthImportTask wermuthImportTask = new WermuthImportTask();
    	for (Entry<String, Integer> aTestEntry : linesAndAssertValues.entrySet()) {
			assertEquals(wermuthImportTask.getVintage(aTestEntry.getKey()),aTestEntry.getValue());
		}    	
    }

    public void testGetUnit()
    {
    	Map<String,BigDecimal> linesAndAssertValues = new HashMap<String,BigDecimal>();
    	
    	linesAndAssertValues.put("116 1 Magnumflasche 1995, pro Lot Sfr. 340–500", new BigDecimal(15));
    	linesAndAssertValues.put("168 1 Doppelmagnumflasche, 1997, OHK pro Lot Sfr. 500–700", new BigDecimal(30));
    	linesAndAssertValues.put("169 1 Imperialflasche, 2007, OHK pro Lot Sfr. 800–1200", new BigDecimal(60));
    	linesAndAssertValues.put("174 3 Flaschen, 2001 pro Lot Sfr. 1800–2100", new BigDecimal(7.5));
    	linesAndAssertValues.put("185 1 Flasche, 2008 pro Dz. Sfr. 1200–1800", new BigDecimal(7.5));
    	linesAndAssertValues.put("187 1 Dutzend Flaschen, 2008, OHK pro Dz. Sfr. 900–1200", new BigDecimal(7.5));
    	linesAndAssertValues.put("230 1 Dutzend Flaschen, 1997, 6er OHK pro Dz. Sfr. 840–1080", new BigDecimal(7.5));
    	linesAndAssertValues.put("246 1 Imperialflasche, 2000, OHK pro Lot Sfr. 1200–1500", new BigDecimal(60));
    	linesAndAssertValues.put("252 1 Jeroboamflasche, 1990, OHK pro Lot Sfr. 2400–3000", new BigDecimal(45));
    	linesAndAssertValues.put("323 2 3/8 Flaschen, 2000 pro Lot Sfr. 200–350", new BigDecimal(3.75));
    	linesAndAssertValues.put("334 6 Flaschen, 2002, OC pro Lot Sfr. 360–480", new BigDecimal(7.5));
    	linesAndAssertValues.put("486 12 3/8 Flaschen, 2001, OHK pro Lot Sfr. 390–480",new BigDecimal(3.75));
    	linesAndAssertValues.put("583 6 Flaschen, 2005, 3er OHK pro Lot Sfr. 540–720",new BigDecimal(7.5));
    	linesAndAssertValues.put("984 2 Flaschen, 1966 pro Lot Sfr. 300–500", new BigDecimal(7.5));
    	linesAndAssertValues.put("326 Total 6 3/8 Flaschen, 1998 pro Lot Sfr. 480–720",new BigDecimal(3.75));
    
    	WermuthImportTask wermuthImportTask = new WermuthImportTask();
    	for (Entry<String, BigDecimal> aTestEntry : linesAndAssertValues.entrySet()) {
			assertEquals(wermuthImportTask.determineSize(aTestEntry.getKey()),aTestEntry.getValue());
		}    	
    }
    
    public void testGetLotNumber()
    {
    	Map<String,String> linesAndAssertValues = new HashMap<String,String>();
    	
    	linesAndAssertValues.put("1 1 Magnumflasche 1995, pro Lot Sfr. 340–500", "1");
    	linesAndAssertValues.put("11 1 Doppelmagnumflasche, 1997, OHK pro Lot Sfr. 500–700", "11");
    	linesAndAssertValues.put("111 1 Imperialflasche, 2007, OHK pro Lot Sfr. 800–1200", "111");
    	linesAndAssertValues.put("1111 3 Flaschen, 2001 pro Lot Sfr. 1800–2100", "1111");
    
    	for (Entry<String, String> aTestEntry : linesAndAssertValues.entrySet()) {
			assertEquals(aTestEntry.getValue(),new WermuthImportTask().getLotNumber(aTestEntry.getKey()));
		}      	
    }
    
}

