package ch.persi.java.vino.importers.steinfels;

import ch.persi.java.vino.importers.ImportingStrategy;
import ch.persi.java.vino.util.SpringUtil;

public class SteinfelsStarter {

	/**
	 * @param args
	 */
	public static void main(String[] args) {
    	ImportingStrategy steinfelsJob = (ImportingStrategy) SpringUtil.getContext().getBean("steinfelsImportJob");
    	steinfelsJob.runImport();
	}

}
