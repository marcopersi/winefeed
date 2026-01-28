package ch.persi.java.vino.importers.steinfels;

import java.util.Set;

import ch.persi.java.vino.importers.ImportingStrategy;
import ch.persi.java.vino.importers.Task;

public class SteinfelsImporter implements ImportingStrategy {
	
	private Set<Task> someTasks;
	
	public void setTasks(Set<Task> theTasks)
	{
		someTasks = theTasks;
	}
	
	@Override
	public void runImport() {
    	
		for (Task aTask : someTasks) {
			// FIXME: guarantee run in 100% sequential order, start second only if first is done
			System.out.println("running task:" + aTask);
			aTask.execute();
		}
		System.out.println("Import successfully done !");
	}
	
}
