package ch.persi.java.vino.importers.wermuth.preparer;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Scanner;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class WermuthSeptember2016Preparer {

	public static void main(String[] args) throws IOException {
		
		//running through characters, drop carriage return /new line if the next line is not the next value in the sequence
		File file = new File("import/Wermuth/WZ-259_19112016_Resultate.txt");

		List<String> someLines = new ArrayList<>();
		Pattern compile = Pattern.compile("^([0-9]{1,4}).*");
		int lastLotNumber = 1;

		try(Scanner input = new Scanner(file))
		{
			while (input.hasNextLine()) {
				String nextLine = input.nextLine();
				Matcher matcher = compile.matcher(nextLine);
				
				if (matcher.matches() && isSequence(matcher.group(1), lastLotNumber))
				{
					someLines.add(nextLine);
					lastLotNumber++;
				} else
				{
					// goto Line before and remove carriage return /new line characters	
					String replaceAll = someLines.get(someLines.size()-1).replaceAll("[\\r\\n]+", "");
					nextLine = replaceAll+" " + nextLine + " ";
					someLines.remove(someLines.size()-1);
					someLines.add(nextLine);
				}
			}
		}
		
		for (String string : someLines) {
//			System.out.println(string);
			System.out.println(string.replaceAll("“|“|«|»|’|”|„", "")
						.replaceAll("CHF", " ")
						.replace(".00", " ")
						.replace(".0 0", " ")
						.replace("AC/MC, ", "")
						.replace("MO, ", "")
						.replace("AC/MO, ", "")
						.replace("MO/IGT, ", "")
						.replace("MO/IGP", "")
						.replace("MO/DOC", "")
						.replace("MO/DOCG,", "")
						.replace("AC/", "")
						.replace("AC/IGT, ", " ")
						.replace("MO/DO, ", ", ")
						.replace("Côte de Nuits, ", " ")
						.replace("Margaux, Margaux", "Margaux, ")
						.replace("Pauillac, ","")
						.replace("St. Julien, "," ")
						.replace("St. Emilion, "," ")
						.replace("Pomerol"," ")
						.replace("Napa Valley, "," ")
						.replace("St. Cruz Mountain, ","")
						.replace("St. Estèphe, ","")
						.replaceAll("Pé|essac.*Lé|eognan, "," ")
						.replace("Sauternes, ", "")
						.replace("Burgenland,", "")
						.replace("Languedoc,", "")
						.replace("Calonge,", "")
						.replace("Barsac,", "")
						.replace("Sauternes,", "")
						.replace("Barsac- Sauternes, ", " ")
						.replace("Côte de Beaune, ", " ")
						.replace("Toscana, ", " ")
						.replace("Haut-Médoc, ", " ")
						.replace("Knights Valley,", " ")
						.replace("PessacsLéognan", " ")
						.replace("Moulis-Médoc, ", " ")
						.replace("Douro, ", "")
						.replace("Limoux, ", "")
						.replace("Mendoza, ", "")
						.replace("Ribera del Duero, ", "")
						.replace("Columbia Valley, ", "")
						.replace("Valpolicella, ", "")
						.replace("Bolgheri", "")
						.replace("Wachau,", "")
						.replace("Rhône", "")
						.replace("crusbourgeois exceptionnels", " ")
						.replace("crus bourgeois exceptionnel", " ")
						.replace("1er grand cru classé ", "")
						.replace("1er grand  cru classé ", "")
						.replace("2e grand cru classé", " ")
						.replace("3e grand cru classé", " ")
						.replace("5e grand cru classé", " ")
						.replace("grand cru exceptionnel ", " ")
						.replace("grand cru classé ", " ")
						.replace("grand cru  classé ", " ")
						.replace("grand cru", "")
						.replace("1 er", " ")
						.replace("1\\s{1,}|er", "")
						.replace("grand cru ", " ")
						.replace("2e", "")
						.replace("2 e", "")
						.replace("3 e", "")
						.replace("5e grandscru", " ")
						.replace("grandcrus", " ")
						.replace("cru", " ")
						.replace("Grand cru, ", " ")
						.replace(" classé ", " ")
						.replace("F lasche", "Flasche")
						.replaceAll("\\s{2}", " ")
						
						);
				}	
		}
	
	
	private static final boolean isSequence(String theNextNumber, int theLastNumber)
	{
		Integer valueOf = Integer.valueOf(theNextNumber);
		if (theLastNumber==valueOf) { return true; };
		for (int i = 1; i<=6;i++) {
			if (theLastNumber+i == valueOf) return true;
		}
		return false;
	}

}
