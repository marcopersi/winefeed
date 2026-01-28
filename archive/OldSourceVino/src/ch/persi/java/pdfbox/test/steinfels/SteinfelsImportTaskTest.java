package ch.persi.java.pdfbox.test.steinfels;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import junit.framework.TestCase;

import org.joda.time.DateTime;

import ch.persi.java.vino.importers.steinfels.SteinfelsImportTask;
import ch.persi.java.vino.util.iTextUtil;

public class SteinfelsImportTaskTest extends TestCase {

	private SteinfelsImportTask steinfelsImportTask = null;
	
	@Override
	public void setUp()
	{
		if (steinfelsImportTask == null)
		{
			steinfelsImportTask = new SteinfelsImportTask();
		}
	}
	
	public void testGetAuctionDate() throws Exception
	{
		String aLine = "Samstag, 2. März 2002Ergebnisliste Steinfels Auktionen, Löwenbräuareal, L";
		DateTime anAuctionDate = SteinfelsImportTask.extractDate(aLine);
		assertEquals(anAuctionDate, new DateTime(2002,3,2,0,0,0,0));
	}
	
	public void testApplyPattern(){
		
//		Pattern compile = java.util.regex.Pattern.compile("^([0-9]*)\\s(.*)\\s([0-9]*)\\s(Flaschen?|Magnum).*([0-9]{4})\\s([0-9]*).*");
		Pattern compile = java.util.regex.Pattern.compile("^([0-9]*)\\s(.*)\\s([0-9]*)\\s(Flaschen?|Magnum).*([0-9]{4})\\s([0-9]*).*");
		
		
		Map<String,Integer> linesAndAssertValues = new HashMap<String,Integer>();
		linesAndAssertValues.put("52 Château Haut Batailley Pauillac 5ème 2 Magnum 1977 200", 2);
		linesAndAssertValues.put("290 Chambolle Musigny Mommessin 1 Jéroboam 3 Liter 1966 240", 1);
    	linesAndAssertValues.put("8 Château Duhart Milon Pauillac 4ème 12 Flaschen OHK 1996 320", 12);
    	linesAndAssertValues.put("10 Château Cantenac Brown Margaux 3ème 12 Flaschen OHK 1993 0", 12);
    	linesAndAssertValues.put("59 Château Mouton Rothschild Pauillac 1er 2 Flaschen 1xTS E-zer, 2xZ 1967 0", 2);
    	linesAndAssertValues.put("328 Ornellaia Tenuta dell'Ornellaia 3 Flaschen 1997 350", 3);
    	linesAndAssertValues.put("347 Sassicaia Tenuta San Guido Toskana 1 Flasche 1993 110", 1);
    	linesAndAssertValues.put("285 Monthélie Moine Père & Fils 12 Flaschen 1985 0", 12);
    	linesAndAssertValues.put("282 Romanée-St-Vivant Domaine Romanée Conti 1 Flasche 1976 360", 1);
    	
		for (Entry<String, Integer> aLine : linesAndAssertValues.entrySet()) {
			String aCleanedLine = aLine.getKey().replace("OHK","");
			Matcher matcher = compile.matcher(aCleanedLine);
			if (matcher.matches())
			{
				for (int i = 0; i<=matcher.groupCount();i++)
				{
					System.out.println(matcher.group(i));
				}
			} else
			{
				System.out.println("Line: " + aCleanedLine + " is NO match !!!!");
			}
			
		}
	}
	
	public void testGetNoOfBottles() throws Exception
	{
//		"^([0-9]*)(\\s.*)(\\s([0-9]*)\\s(Flaschen?)|(Magnum)).*([0-9]{4})\\s([0-9]*).*"
		Map<String,Integer> linesAndAssertValues = new HashMap<String,Integer>();
		linesAndAssertValues.put("52 Château Haut Batailley Pauillac 5ème 2 Magnum 1977 200", 2);
		linesAndAssertValues.put("290 Chambolle Musigny Mommessin 1 Jéroboam 3 Liter 1966 240", 1);
    	linesAndAssertValues.put("8 Château Duhart Milon Pauillac 4ème 12 Flaschen OHK 1996 320", 12);
    	linesAndAssertValues.put("10 Château Cantenac Brown Margaux 3ème 12 Flaschen OHK 1993 0", 12);
    	linesAndAssertValues.put("59 Château Mouton Rothschild Pauillac 1er 2 Flaschen 1xTS E-zer, 2xZ 1967 0", 2);
    	linesAndAssertValues.put("328 Ornellaia Tenuta dell'Ornellaia 3 Flaschen 1997 350", 3);
    	linesAndAssertValues.put("347 Sassicaia Tenuta San Guido Toskana 1 Flasche 1993 110", 1);
    	linesAndAssertValues.put("285 Monthélie Moine Père & Fils 12 Flaschen 1985 0", 12);
    	linesAndAssertValues.put("282 Romanée-St-Vivant Domaine Romanée Conti 1 Flasche 1976 360", 1);
    	
		for (Entry<String, Integer> aLine : linesAndAssertValues.entrySet()) {
			assertEquals(aLine.getValue(),steinfelsImportTask.getNoOfBottles(aLine.getKey()));
		}
		
	}
	
	public void testFailingLine()
	{
		String theLine = "278 Mixed Lots 7 Flaschen 0 0";
		assertFalse(steinfelsImportTask.isRecordLine(theLine));
		assertNull(steinfelsImportTask.getNoOfBottles(theLine));
		assertNull(steinfelsImportTask.getOrigin(theLine));
		assertNull(steinfelsImportTask.getLotNumber(theLine));
		assertNull(steinfelsImportTask.getParkerRating(theLine));
		assertNull(steinfelsImportTask.getVintage(theLine));
	}

	public void testFindProblematicPart()
	{
		String line1= "4 Ch‰teau Lascombes Margaux 2ème 12 Flaschen OHK 1996 250";
		assertTrue(steinfelsImportTask.isRecordLine(line1));
	}
	
	public void testFailingRecordLine()
	{
		assertFalse(steinfelsImportTask.isRecordLine("278 Mixed Lots 7 Flaschen 0 0"));
	}
	
	public void testGetLotNumber() throws Exception
	{
		Map<String,String> linesAndAssertValues = new HashMap<String,String>();
    	linesAndAssertValues.put("290 Chambolle Musigny Mommessin 1 Jéroboam 3 Liter 1966 240", "290");
    	linesAndAssertValues.put("8 Château Duhart Milon Pauillac 4ème 12 Flaschen OHK 1996 320", "8");
    	linesAndAssertValues.put("10 Château Cantenac Brown Margaux 3ème 12 Flaschen OHK 1993 0", "10");
    	linesAndAssertValues.put("59 Château Mouton Rothschild Pauillac 1er 2 Flaschen 1xTS E-zer, 2xZ 1967 0", "59");
    	linesAndAssertValues.put("328 Ornellaia Tenuta dell'Ornellaia 3 Flaschen 1997 350", "328");
    	linesAndAssertValues.put("347 Sassicaia Tenuta San Guido Toskana 1 Flasche 1993 110", "347");
    	linesAndAssertValues.put("285 Monthélie Moine Père & Fils 12 Flaschen 1985 0", "285");
    	linesAndAssertValues.put("282 Romanée-St-Vivant Domaine Romanée Conti 1 Flasche 1976 360", "282");
    	
		for (Entry<String, String> aLine : linesAndAssertValues.entrySet()) {
			assertEquals(aLine.getValue(),steinfelsImportTask.getLotNumber(aLine.getKey()));
		}
		
	}
	
	public void testGetVintage() throws Exception
	{
		Map<String,Integer> linesAndAssertValues = new HashMap<String,Integer>();
		linesAndAssertValues.put("1 Château Le Fournas Bernadotte Haut-Médoc 12 Flaschen OHK 1976 210", 1976);
		linesAndAssertValues.put("2 Château Le Fournas Bernadotte Haut-Médoc 12 Flaschen OHK 1976 220", 1976);
		linesAndAssertValues.put("3 Château Le Fournas Bernadotte Haut-Médoc 8 Flaschen OHK 1976 140", 1976);
		linesAndAssertValues.put("290 Chambolle Musigny Mommessin 1 Jéroboam 3 Liter 1966 240", 1966);
    	linesAndAssertValues.put("8 Château Duhart Milon Pauillac 4ème 12 Flaschen OHK 1996 320", 1996);
    	linesAndAssertValues.put("10 Château Cantenac Brown Margaux 3ème 12 Flaschen OHK 1993 0", 1993);
    	linesAndAssertValues.put("59 Château Mouton Rothschild Pauillac 1er 2 Flaschen 1xTS E-zer, 2xZ 1967 0", 1967);
    	linesAndAssertValues.put("328 Ornellaia Tenuta dell'Ornellaia 3 Flaschen 1997 350", 1997);
    	linesAndAssertValues.put("347 Sassicaia Tenuta San Guido Toskana 1 Flasche 1993 110", 1993);
    	linesAndAssertValues.put("285 Monthélie Moine Père & Fils 12 Flaschen 1985 0", 1985);
    	linesAndAssertValues.put("282 Romanée-St-Vivant Domaine Romanée Conti 1 Flasche 1976 360", 1976);
    	
		for (Entry<String, Integer> aLine : linesAndAssertValues.entrySet()) {
			assertEquals(aLine.getValue(),steinfelsImportTask.getVintage(aLine.getKey()));
		}	
	}
	
	public void testDumpLines() throws Exception
	{
		List<String> someLines = iTextUtil.getLines("import/Steinfels/315.pdf");
		assertNotNull(someLines);
		assertTrue(someLines.size()>0);
		for (String aLine : someLines) {
			assertNotNull(aLine);
			System.out.println(aLine);
		}
	}
	
	public void testDumpNonRecordLines() throws Exception
	{
		List<String> someLines = iTextUtil.getLines("import/Steinfels/315.pdf");
		assertNotNull(someLines);
		assertTrue(someLines.size()>0);
		int aCounter = 0;
		for (String aLine : someLines) {
			if (!steinfelsImportTask.isRecordLine(aLine))
			{
				System.out.println("NO record line: " + aLine);
				aCounter++;
			}
		}
		System.out.println("Found " + aCounter + " non record lines , finally");
	}
	
	public void testDetermineSize()
	{
		Map<String,BigDecimal> linesAndAssertValues = new HashMap<String,BigDecimal>();
    	linesAndAssertValues.put("545 Château Le Fournas Bernadotte Haut-Médoc 2 Magnum 1983 70", new BigDecimal(15));
    	linesAndAssertValues.put("546 Château La Tour Fonrazade Saint Emilion 2 Magnum 1986 80", new BigDecimal(15));
    	linesAndAssertValues.put("59 Château Mouton Rothschild Pauillac 1er 2 Flaschen 1xTS E-zer, 2xZ 1967 0", new BigDecimal(7.5));
    	linesAndAssertValues.put("328 Ornellaia Tenuta dell'Ornellaia 3 3/8 1997 350", new BigDecimal(3.75));
    	linesAndAssertValues.put("290 Chambolle Musigny Mommessin 1 Jéroboam 3 Liter 1966 240", new BigDecimal(45));
    	for (Entry<String, BigDecimal> aLine : linesAndAssertValues.entrySet()) {
			assertEquals(aLine.getValue(),steinfelsImportTask.determineSize(aLine.getKey()));
		}	
	}
	
}
