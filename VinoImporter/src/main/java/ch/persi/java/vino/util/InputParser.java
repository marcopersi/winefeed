package ch.persi.java.vino.util;

import java.util.List;

public interface InputParser {

	/**
	 * 
	 * @param theFileName
	 * @return a {@link List} of Strings contained in the file
	 */
	List<String> parse(String theFileName);
}
