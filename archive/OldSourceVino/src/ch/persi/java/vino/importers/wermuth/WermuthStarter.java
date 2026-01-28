package ch.persi.java.vino.importers.wermuth;

import ch.persi.java.vino.importers.ImportingStrategy;
import ch.persi.java.vino.util.SpringUtil;

public class WermuthStarter {

	/**
	 * @param args
	 */
	public static void main(String[] args) {
    	ImportingStrategy wermuthImport = (ImportingStrategy) SpringUtil.getContext().getBean("wermuthImportJob");
    	wermuthImport.runImport();
	}

}
