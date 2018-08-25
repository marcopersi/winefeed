package ch.persi.java.vino.importers.wermuth.format2015;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * This preparer checks if there is a three digit numeric tag in front of the lot no.
 * If so, this tag gets removed.
 * 
 * @author marcopersi
 *
 */
public class ResultFilebasedLotLinePreparer {

	// a pattern to check if there is a three digit tag in front of the lot no. of the record.
	public static Pattern aWrongLinePattern = Pattern.compile("^[0-9]{3}\\s([0-9]{1,3}.*)");
	
	public static List<String> prepare(List<String> theLines) {
		List<String> somePreparedLines = new ArrayList<>();
		
		for (String aLine : theLines) {
			Matcher matcher = aWrongLinePattern.matcher(aLine);
			if (matcher.matches()) {
				somePreparedLines.add(matcher.group(1));
			}
		}
		return somePreparedLines;
	}

}
