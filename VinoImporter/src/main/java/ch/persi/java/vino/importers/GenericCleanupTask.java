package ch.persi.java.vino.importers;

import java.io.File;


public class GenericCleanupTask implements Task {

	private String doneFilesLocation = null;
	private String importFilesLocation = null;
	
	public void setImportFilesLocation(final String theDirectory)
	{
		importFilesLocation=theDirectory;
	}
	
	public void setDoneFilesLocation(final String theDirectory)
	{
		doneFilesLocation=theDirectory;
	}
	
	@Override
	public void execute() {
		/*
		 FIXME: code fuer handling files im import ist redundant, 1 x hier, 1 x WermuthImporter.
		 eigentlich sollte das ein eigener Task werden (Composite Task oder so) der dann den injected Task
		 einfach ausführt (Task.execute) der injected task ist einmal ein import das andere mal ein cleanup
		*/
		File[] someFiles = new File(importFilesLocation).listFiles();

		if (someFiles != null) {
			for (File aFile : someFiles) {
				aFile.renameTo(new File(doneFilesLocation + aFile.getName()));
			}
		}
	}

}
