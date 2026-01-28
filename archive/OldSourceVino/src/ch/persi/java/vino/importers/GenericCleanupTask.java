package ch.persi.java.vino.importers;

import java.io.File;


public class GenericCleanupTask implements Task {

	private String doneFilesLocation = null;
	private String importFilesLocation = null;
	
	public void setImportFilesLocation(String theDirectory)
	{
		importFilesLocation=theDirectory;
	}
	
	public void setDoneFilesLocation(String theDirectory)
	{
		doneFilesLocation=theDirectory;
	}
	
	@Override
	public void execute() {
		// FIXME: code für handling files im import ist redundant, 1 x hier, 1 x WermuthImporter.
		// eigentlich sollte das ein eigener Task werden (Composite Task oder so) der dann den injected Task
		// einfach ausfŸhrt (Task.execute) der injected task ist einmal ein import das andere mal ein cleanup
		File[] listFiles = new File(importFilesLocation).listFiles(); 
    	
    	for (File file : listFiles) {
			file.renameTo(new File(doneFilesLocation + file.getName()));
		}

	}

}
