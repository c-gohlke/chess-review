export function Settings({
	users,
	player,
	onChoose,
}: {
	users: string[];
	player: string | null;
	onChoose: (username: string) => void;
}) {
	return (
		<section className="mx-auto w-full max-w-[600px]">
			<h2 className="mb-2 text-lg font-bold">Settings</h2>
			{users.length === 0 ? (
				<p>No players yet. Import games from the Games tab.</p>
			) : (
				<label className="flex flex-col gap-1">
					<span>Player</span>
					<select
						className="min-h-11 w-full rounded border px-3"
						value={player ?? ""}
						onChange={(event) => onChoose(event.target.value)}
					>
						{users.map((user) => (
							<option key={user} value={user}>
								{user}
							</option>
						))}
					</select>
				</label>
			)}
		</section>
	);
}
